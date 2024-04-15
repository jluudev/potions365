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
    total_green_ml_delivered = sum(barrel.ml_per_barrel * barrel.quantity for barrel in barrels_delivered if "GREEN" in barrel.sku)
    total_red_ml_delivered = sum(barrel.ml_per_barrel * barrel.quantity for barrel in barrels_delivered if "RED" in barrel.sku)
    total_blue_ml_delivered = sum(barrel.ml_per_barrel * barrel.quantity for barrel in barrels_delivered if "BLUE" in barrel.sku)
    
    new_gold = sum(barrel.price * barrel.quantity for barrel in barrels_delivered)

    with db.engine.begin() as connection:
        sql_to_execute = """
            UPDATE global_inventory
            SET num_green_ml = num_green_ml + :green_ml_added,
                num_red_ml = num_red_ml + :red_ml_added,
                num_blue_ml = num_blue_ml + :blue_ml_added,
                gold = gold - :sub_gold
        """
        connection.execute(sqlalchemy.text(sql_to_execute), {
            "green_ml_added": total_green_ml_delivered,
            "red_ml_added": total_red_ml_delivered,
            "blue_ml_added": total_blue_ml_delivered,
            "sub_gold": new_gold
        })

    print(f"Barrels delivered: {barrels_delivered}, Order ID: {order_id}")

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    plan = []
    sql_to_execute = """SELECT num_green_potions, num_red_potions, num_blue_potions, gold, num_green_ml, num_red_ml, num_blue_ml FROM global_inventory"""
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute)).first()
        if result:
            num_green_potions, num_red_potions, num_blue_potions, gold, num_green_ml, num_red_ml, num_blue_ml = result
            
            for barrel in wholesale_catalog:
                if "SMALL_GREEN_BARREL" in barrel.sku and num_green_potions < 10 and gold >= barrel.price and (num_green_ml + barrel.ml_per_barrel) <= 10000:
                    plan.append({"sku": barrel.sku, "quantity": (gold // barrel.price)})
                    break

                elif "SMALL_RED_BARREL" in barrel.sku and num_red_potions < 10 and gold >= barrel.price and (num_red_ml + barrel.ml_per_barrel) <= 10000:
                    plan.append({"sku": barrel.sku, "quantity": (gold // barrel.price)})
                    break

                elif "SMALL_BLUE_BARREL" in barrel.sku and num_blue_potions < 10 and gold >= barrel.price and (num_blue_ml + barrel.ml_per_barrel) <= 10000:
                    plan.append({"sku": barrel.sku, "quantity": (gold // barrel.price)})
                    break

    return plan




