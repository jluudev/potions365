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

@router.post("/deliver/{order_id}/")
def post_deliver_bottles(potions_delivered: list[PotionInventory]):
    with db.engine.begin() as connection:
        total_used_ml = [0, 0, 0, 0]

        for potion in potions_delivered:
            potion_transaction_id = connection.execute(sqlalchemy.text("""
                INSERT INTO potions_transactions (description)
                VALUES (:description)
                RETURNING id
                """), {"description": f"Bottled: {potion}"}).first().id
            
            connection.execute(sqlalchemy.text("""
                INSERT INTO potions_entries (potion_sku, change, transaction_id)
                SELECT potions.sku, :change, :transaction_id
                FROM potions WHERE potions.red = :red AND potions.green = :green 
                AND potions.blue = :blue AND potions.dark = :dark
                """), {"change": potion.quantity, "transaction_id": potion_transaction_id,
                        "red": potion.potion_type[0], "green": potion.potion_type[1],
                        "blue": potion.potion_type[2], "dark": potion.potion_type[3]})

            for i in range(len(potion.potion_type)):
                potion_ml = potion.potion_type[i] * potion.quantity  # Calculate the total ml used for the potion type
                total_used_ml[i] += potion_ml

        # Update global_inventory
        transaction_id = connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_transactions (description)
            VALUES (:description)
            RETURNING id
            """), {"description": f"Bottled: {potions_delivered}"}).first().id

        connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_entries
                (change_gold, change_red_ml, change_green_ml, change_blue_ml, change_dark_ml, transaction_id)
            VALUES (:gold, :num_red_ml, :num_green_ml, :num_blue_ml, :num_dark_ml, :transaction_id)
            """), {"gold": 0, "num_red_ml": -total_used_ml[0], "num_green_ml": -total_used_ml[1],
                  "num_blue_ml": -total_used_ml[2], "num_dark_ml": -total_used_ml[3], "transaction_id": transaction_id})

    return "OK"



@router.post("/plan")
def get_bottle_plan():
    ml_reserve_percentage = 0.2  # Percentage of ml to reserve

    with db.engine.begin() as connection:
        potion_query = """
            SELECT red, green, blue, dark
            FROM potions
            LEFT JOIN potions_entries AS pe ON pe.potion_sku = potions.sku
            GROUP BY red, green, blue, dark
        """
        potions_result = connection.execute(sqlalchemy.text(potion_query)).fetchall()
        total_potions = connection.execute(sqlalchemy.text("""SELECT COALESCE(SUM(change), 0) FROM potions_entries""")).fetchone()[0]

        global_inventory_query = """
            SELECT SUM(change_red_ml) as num_red_ml, SUM(change_green_ml) as num_green_ml,
                   SUM(change_blue_ml) as num_blue_ml, SUM(change_dark_ml) as num_dark_ml
            FROM inventory_entries
        """
        global_inventory_result = connection.execute(sqlalchemy.text(global_inventory_query)).fetchone()
        if global_inventory_result:
            num_red_ml, num_green_ml, num_blue_ml, num_dark_ml = global_inventory_result

        bottle_plan = []

        # Calculate available ml for each color after reservation
        available_red_ml = max(0, num_red_ml - int(ml_reserve_percentage * num_red_ml))
        available_green_ml = max(0, num_green_ml - int(ml_reserve_percentage * num_green_ml))
        available_blue_ml = max(0, num_blue_ml - int(ml_reserve_percentage * num_blue_ml))
        available_dark_ml = max(0, num_dark_ml - int(ml_reserve_percentage * num_dark_ml))

        # Shuffle results
        random.shuffle(potions_result)

        for potion_data in potions_result:
            red_quantity, green_quantity, blue_quantity, dark_quantity = potion_data

            max_bottles_possible = min(
                available_red_ml // red_quantity if red_quantity > 0 else float('inf'),
                available_green_ml // green_quantity if green_quantity > 0 else float('inf'),
                available_blue_ml // blue_quantity if blue_quantity > 0 else float('inf'),
                available_dark_ml // dark_quantity if dark_quantity > 0 else float('inf')
            )
            num_bottles = min(max_bottles_possible, 5)

            # print("Available ml: ", available_red_ml, available_green_ml, available_blue_ml, available_dark_ml)

            # Check if the sum of each potion index doesn't exceed available ml
            if (
                red_quantity * num_bottles <= available_red_ml and
                green_quantity * num_bottles <= available_green_ml and
                blue_quantity * num_bottles <= available_blue_ml and
                dark_quantity * num_bottles <= available_dark_ml
            ):
                if num_bottles > 0:
                    available_red_ml -= red_quantity * num_bottles
                    available_green_ml -= green_quantity * num_bottles
                    available_blue_ml -= blue_quantity * num_bottles
                    available_dark_ml -= dark_quantity * num_bottles

                    total_potions += num_bottles
                    bottle_plan.append(
                        {
                            "potion_type": [red_quantity, green_quantity, blue_quantity, dark_quantity],
                            "quantity": num_bottles
                        }
                    )
            # print(total_potions)
            if (total_potions >= 40):
                break

    return bottle_plan


if __name__ == "__main__":
    print(get_bottle_plan())