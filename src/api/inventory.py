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
        global_inventory_result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory")).first()
        
        total_potions_result = connection.execute(sqlalchemy.text("SELECT SUM(quantity) AS total_potions FROM potions")).first()
    
    total_potions = total_potions_result.total_potions if total_potions_result else 0

    ml_in_barrels = (global_inventory_result.num_green_ml + global_inventory_result.num_red_ml + global_inventory_result.num_blue_ml + global_inventory_result.num_dark_ml) if global_inventory_result else 0

    total_potions = min(total_potions, 50)
    ml_in_barrels = min(ml_in_barrels, 10000)

    return {
        "number_of_potions": total_potions,
        "ml_in_barrels": ml_in_barrels,
        "gold": global_inventory_result.gold if global_inventory_result else 0
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
