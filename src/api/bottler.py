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
    """ """
    print(f"Potions delivered: {potions_delivered}, Order ID: {order_id}")

    total_green_potions_delivered = sum(potion.quantity for potion in potions_delivered if potion.potion_type == [0, 100, 0, 0])
    
    total_ml_to_subtract = 100 * total_green_potions_delivered

    # Update the global inventory with the new quantity of green potions and adjust the ml
    sql_to_execute = """
                UPDATE global_inventory
                SET num_green_potions = num_green_potions + :quantity_added,
                    num_green_ml = num_green_ml - :ml_subtracted
            """
    with db.engine.begin() as connection:
            connection.execute(sqlalchemy.text(sql_to_execute), {"quantity_added": total_green_potions_delivered, "ml_subtracted": total_ml_to_subtract})

    return {"msg": "OK", "total_potions_added": total_green_potions_delivered}

@router.post("/plan")
def get_bottle_plan():
    """
    Go from barrel to bottle.
    """

    # Each bottle has a quantity of what proportion of red, blue, and
    # green potion to add.
    # Expressed in integers from 1 to 100 that must sum up to 100.

    # Initial logic: bottle all barrels into red potions.

    ml_per_bottle = 100  

    with db.engine.begin() as connection:
        inventory_check_sql = "SELECT num_green_ml FROM global_inventory"
        result = connection.execute(sqlalchemy.text(inventory_check_sql)).scalar()

        if result >= 100:
            return {
                "potion_type": [0, 100, 0, 0],
                "quantity": result // 100
            }
    return []

if __name__ == "__main__":
    print(get_bottle_plan())