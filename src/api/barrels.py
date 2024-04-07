from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    """ """
    # Calculate the total ml of green potion delivered
    total_ml_delivered = sum(barrel.ml_per_barrel * barrel.quantity for barrel in barrels_delivered if "GREEN" in barrel.sku)

    with db.engine.begin() as connection:
        sql_to_execute = """
            UPDATE global_inventory
            SET num_green_ml = num_green_ml + :ml_added
        """
        connection.execute(sqlalchemy.text(sql_to_execute), {"ml_added" : total_ml_delivered})

    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return {"message": "OK", "total_ml_added": total_ml_delivered}

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    print(wholesale_catalog)

    plan = []
    sql_to_execute = """SELECT num_green_potions, gold FROM global_inventory"""
    with db.engine.begin() as connection:
        num_green_potions, gold = connection.execute(sqlalchemy.text(sql_to_execute)).first()

        if num_green_potions < 10:
            for barrel in wholesale_catalog:
                if "GREEN" in barrel.sku and gold >= barrel.price:
                    plan.append({"sku": barrel.sku, "quantity": (gold // barrel.price)})
                    break 

    return plan


