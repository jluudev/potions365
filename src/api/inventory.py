from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("""
            SELECT 
                COALESCE(SUM(gie.change_gold), 0) AS gold,
                COALESCE(SUM(gie.change_red_ml + gie.change_green_ml + gie.change_blue_ml + gie.change_dark_ml), 0) AS ml_in_barrels,
                COALESCE(SUM(pe.change), 0) AS number_of_potions
            FROM inventory_entries AS gie
            FULL JOIN potions_entries AS pe ON gie.transaction_id = pe.transaction_id
        """)).first()

    return {
        "number_of_potions": result.number_of_potions,
        "ml_in_barrels": result.ml_in_barrels,
        "gold": result.gold
    }

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    # with db.engine.begin() as connection:
    #   result = connection.execute(sqlalchemy.text(sql_to_execute))
    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """
    # with db.engine.begin() as connection:
    #   result = connection.execute(sqlalchemy.text(sql_to_execute))
    return "OK"
