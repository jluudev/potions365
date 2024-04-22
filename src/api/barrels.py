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
    total_dark_ml_delivered = sum(barrel.ml_per_barrel * barrel.quantity for barrel in barrels_delivered if "DARK" in barrel.sku)
    
    new_gold = sum(barrel.price * barrel.quantity for barrel in barrels_delivered)

    with db.engine.begin() as connection:
        sql_to_execute = """
            UPDATE global_inventory
            SET num_green_ml = num_green_ml + :green_ml_added,
                num_red_ml = num_red_ml + :red_ml_added,
                num_blue_ml = num_blue_ml + :blue_ml_added,
                num_dark_ml = num_blue_ml + :dark_ml_added,
                gold = gold - :sub_gold
        """
        connection.execute(sqlalchemy.text(sql_to_execute), {
            "green_ml_added": total_green_ml_delivered,
            "red_ml_added": total_red_ml_delivered,
            "blue_ml_added": total_blue_ml_delivered,
            "dark_ml_added": total_dark_ml_delivered,
            "sub_gold": new_gold
        })

    print(f"Barrels delivered: {barrels_delivered}, Order ID: {order_id}")

    return "OK"


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    plan = []
    with db.engine.begin() as connection:
        # Retrieve global inventory data
        result = connection.execute(sqlalchemy.text("SELECT gold, num_green_ml, num_red_ml, num_blue_ml, num_dark_ml FROM global_inventory")).first()
        if result:
            gold, num_green_ml, num_red_ml, num_blue_ml, num_dark_ml = result

            # Retrieve potion inventory data
            potion_inventory = {}
            potion_data = connection.execute(sqlalchemy.text("SELECT name, quantity FROM potions")).fetchall()
            for potion in potion_data:
                name, quantity = potion
                potion_inventory[name] = quantity

            most_needed_potions = sorted(potion_inventory.keys(), key=lambda sku: potion_inventory[sku], reverse=True)[:6]

            # Filter out MINI barrels and barrels producing the most needed potions from the catalog
            filtered_catalog = [barrel for barrel in wholesale_catalog if "MINI" not in barrel.sku and barrel.sku not in most_needed_potions]

            # Sort the catalog by price
            sorted_catalog = sorted(filtered_catalog, key=lambda barrel: barrel.price)

            for potion_sku in most_needed_potions:
                if potion_inventory.get(potion_sku, 0) < 50:  # Check if potion type needs to be replenished
                    ml_needed = max(0, 10000 - (num_green_ml + num_red_ml + num_blue_ml + num_dark_ml))
                    for barrel in sorted_catalog:
                        if (barrel.ml_per_barrel > 0 and (num_green_ml + num_red_ml + num_blue_ml + num_dark_ml + barrel.ml_per_barrel <= 10000)
                                and (gold >= barrel.price) and (potion_inventory.get(potion_sku, 0) < 50)):
                            max_quantity = min(gold // barrel.price, barrel.quantity, (50 - potion_inventory.get(potion_sku, 0)), ml_needed // barrel.ml_per_barrel)
                            if max_quantity > 0:
                                total_price = barrel.price * max_quantity
                                plan.append({"sku": barrel.sku, "quantity": max_quantity})
                                gold -= total_price
                                potion_inventory[potion_sku] = potion_inventory.get(potion_sku, 0) + max_quantity
                                ml_needed -= max_quantity * barrel.ml_per_barrel

    return plan







