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
      result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
    
    total_potions = result.num_green_potions + result.num_red_potions + result.num_blue_potions
    ml_in_barrels = result.num_green_ml + result.num_red_ml + result.num_blue_ml

    return {
        "number_of_potions": total_potions,
        "ml_in_barrels": ml_in_barrels if ml_in_barrels <= 10000 else 10000,
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
