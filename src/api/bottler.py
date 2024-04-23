from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import random

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
    ml_reserve_percentage = 0.2  # Percentage of ml to reserve

    with db.engine.begin() as connection:
        potion_query = """
            SELECT red, green, blue, dark, quantity 
            FROM potions
        """
        potions_result = connection.execute(sqlalchemy.text(potion_query)).fetchall()

        random.shuffle(potions_result)

        inventory_query = """
            SELECT num_red_ml, num_green_ml, num_blue_ml, num_dark_ml
            FROM global_inventory
        """
        inventory_result = connection.execute(sqlalchemy.text(inventory_query)).fetchone()
        if inventory_result:
            num_red_ml, num_green_ml, num_blue_ml, num_dark_ml = inventory_result

        bottle_plan = []

        total_red_ml_required = sum(potion_data[0] for potion_data in potions_result)
        total_green_ml_required = sum(potion_data[1] for potion_data in potions_result)
        total_blue_ml_required = sum(potion_data[2] for potion_data in potions_result)
        total_dark_ml_required = sum(potion_data[3] for potion_data in potions_result)
        total_potions_in_table = sum(potion_data[4] for potion_data in potions_result)

        reserve_red_ml = int(ml_reserve_percentage * total_red_ml_required)
        reserve_green_ml = int(ml_reserve_percentage * total_green_ml_required)
        reserve_blue_ml = int(ml_reserve_percentage * total_blue_ml_required)
        reserve_dark_ml = int(ml_reserve_percentage * total_dark_ml_required)

        available_red_ml = max(0, num_red_ml - reserve_red_ml)
        available_green_ml = max(0, num_green_ml - reserve_green_ml)
        available_blue_ml = max(0, num_blue_ml - reserve_blue_ml)
        available_dark_ml = max(0, num_dark_ml - reserve_dark_ml)

        for potion_data in potions_result:
            red_quantity, green_quantity, blue_quantity, dark_quantity, quantity = potion_data

            if quantity <= 5 and total_potions_in_table <= 50:
                # Check if there's enough ml of each color to bottle this potion type
                if (red_quantity <= available_red_ml or red_quantity == 0) and \
                   (green_quantity <= available_green_ml or green_quantity == 0) and \
                   (blue_quantity <= available_blue_ml or blue_quantity == 0) and \
                   (dark_quantity <= available_dark_ml or dark_quantity == 0):
                    try:
                        num_bottles = min(
                            5,
                            available_red_ml // red_quantity if red_quantity > 0 else float('inf'),
                            available_green_ml // green_quantity if green_quantity > 0 else float('inf'),
                            available_blue_ml // blue_quantity if blue_quantity > 0 else float('inf'),
                            available_dark_ml // dark_quantity if dark_quantity > 0 else float('inf')
                        )
                    except ZeroDivisionError:
                        num_bottles = float('inf')
                    bottle_plan.append(
                        {
                            "potion_type": [red_quantity, green_quantity, blue_quantity, dark_quantity],
                            "quantity": num_bottles
                        }
                    )

                    # Update the available ml for each color
                    if red_quantity > 0:
                        available_red_ml -= red_quantity * num_bottles
                    if green_quantity > 0:
                        available_green_ml -= green_quantity * num_bottles
                    if blue_quantity > 0:
                        available_blue_ml -= blue_quantity * num_bottles
                    if dark_quantity > 0:
                        available_dark_ml -= dark_quantity * num_bottles

        return bottle_plan

if __name__ == "__main__":
    print(get_bottle_plan())