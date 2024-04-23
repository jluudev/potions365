from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")

    # Dictionary to hold the total ml to subtract for each color
    ml_to_subtract = {"red": 0, "green": 0, "blue": 0, "dark": 0}

    # Calculate the total ml to subtract for each color based on delivered potions
    for potion in potions_delivered:
        for i, ml in enumerate(potion.potion_type):
            ml_to_subtract["red"] += ml * potion.quantity if i == 0 else 0
            ml_to_subtract["green"] += ml * potion.quantity if i == 1 else 0
            ml_to_subtract["blue"] += ml * potion.quantity if i == 2 else 0
            ml_to_subtract["dark"] += ml * potion.quantity if i == 3 else 0

    # Update the global inventory with the new quantities and adjust the ml
    sql_to_execute = """
        UPDATE global_inventory
        SET num_red_ml = num_red_ml - :red_ml_subtracted,
            num_green_ml = num_green_ml - :green_ml_subtracted,
            num_blue_ml = num_blue_ml - :blue_ml_subtracted,
            num_dark_ml = num_dark_ml - :dark_ml_subtracted
    """

    update_potions_sql = """
        UPDATE potions
        SET quantity = quantity + :quantity
        WHERE red = :red AND green = :green AND blue = :blue AND dark = :dark
    """

    with db.engine.begin() as connection:
        connection.execute(
            sqlalchemy.text(sql_to_execute),
            {
                "red_ml_subtracted": ml_to_subtract["red"],
                "green_ml_subtracted": ml_to_subtract["green"],
                "blue_ml_subtracted": ml_to_subtract["blue"],
                "dark_ml_subtracted": ml_to_subtract["dark"],
            },
        )
        
        for potion in potions_delivered:
            connection.execute(
                sqlalchemy.text(update_potions_sql),
                {
                    "red": potion.potion_type[0],
                    "green": potion.potion_type[1],
                    "blue": potion.potion_type[2],
                    "dark": potion.potion_type[3],
                    "quantity": potion.quantity
                }
            )

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    ml_per_bottle = 100  # Milliliters per bottle
    ml_reserve_percentage = 0.2 # Percentage of ml to reserve

    with db.engine.begin() as connection:
        # Fetch potion types and their quantities from the potions table
        potion_query = """
            SELECT red, green, blue, dark, quantity 
            FROM potions
        """
        potions_result = connection.execute(sqlalchemy.text(potion_query)).fetchall()

        # Fetch available ml for each color from the global_inventory table
        inventory_query = """
            SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml
            FROM global_inventory
        """
        inventory_result = connection.execute(sqlalchemy.text(inventory_query)).fetchone()
        if inventory_result:
            num_red_ml, num_green_ml, num_blue_ml, num_dark_ml = inventory_result

        bottle_plan = []

        num_potions_listed = 0
        for potion_data in potions_result:
            red_quantity, green_quantity, blue_quantity, dark_quantity, quantity = potion_data

            if quantity <= 10 and num_potions_listed < 6:
                # Calculate the total ml for this potion type
                total_red_ml = red_quantity
                total_green_ml = green_quantity
                total_blue_ml = blue_quantity
                total_dark_ml = dark_quantity

                # Calculate the amount of ml to reserve
                reserve_red_ml = int(ml_reserve_percentage * total_red_ml)
                reserve_green_ml = int(ml_reserve_percentage * total_green_ml)
                reserve_blue_ml = int(ml_reserve_percentage * total_blue_ml)
                reserve_dark_ml = int(ml_reserve_percentage * total_dark_ml)

                # Calculate the available ml for bottling
                available_red_ml = num_red_ml - reserve_red_ml
                available_green_ml = num_green_ml - reserve_green_ml
                available_blue_ml = num_blue_ml - reserve_blue_ml
                available_dark_ml = num_dark_ml - reserve_dark_ml

                # Check if there's enough ml of each color to bottle this potion type, some potions may be all of one color or a mix of colors in different quantities, then calculate the number of bottles that can be filled, and add the potion type to the plan
                if (available_red_ml >= total_red_ml and
                    available_green_ml >= total_green_ml and
                    available_blue_ml >= total_blue_ml and
                    available_dark_ml >= total_dark_ml):
                    num_bottles = max(
                        available_red_ml // ml_per_bottle,
                        available_green_ml // ml_per_bottle,
                        available_blue_ml // ml_per_bottle,
                        available_dark_ml // ml_per_bottle
                    )
                    if num_bottles > 0:
                        bottle_plan.append(
                            {
                                "potion_type": [red_quantity, green_quantity, blue_quantity, dark_quantity],
                                "quantity": num_bottles
                            }
                        )
                    num_potions_listed += 1
                

        return bottle_plan


if __name__ == "__main__":
    print(get_bottle_plan())