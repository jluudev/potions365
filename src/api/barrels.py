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
    colors_in_plan = set()  # Set to keep track of colors
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text("SELECT gold, num_green_ml, num_red_ml, num_blue_ml, num_dark_ml FROM global_inventory")).first()
        if result:
            gold, num_green_ml, num_red_ml, num_blue_ml, num_dark_ml = result

            potion_inventory = {}
            potion_data = connection.execute(sqlalchemy.text("SELECT name, quantity FROM potions")).fetchall()
            for potion in potion_data:
                name, quantity = potion
                potion_inventory[name] = quantity

            most_needed_potions = sorted(potion_inventory.keys(), key=lambda sku: potion_inventory[sku], reverse=True)[:6]

            # Filter out MINI barrels
            filtered_catalog = [barrel for barrel in wholesale_catalog if "MINI" not in barrel.sku and barrel.sku not in most_needed_potions]

            sorted_catalog = sorted(filtered_catalog, key=lambda barrel: barrel.price / barrel.ml_per_barrel if barrel.ml_per_barrel > 0 else float('inf'))

            dark_barrel_added = False

            for barrel in sorted_catalog:
                color = barrel.sku.split("_")[1].upper()
                # If a dark barrel is available and hasn't been added yet, prioritize it
                if color == "DARK" and not dark_barrel_added:
                    if (barrel.ml_per_barrel > 0 and (num_green_ml + num_red_ml + num_blue_ml + num_dark_ml + barrel.ml_per_barrel <= 10000)
                            and (gold >= barrel.price)):
                        plan.append({"sku": barrel.sku, "quantity": 1}) # Only every buy 1 barrel for now
                        colors_in_plan.add(color)
                        gold -= barrel.price
                        dark_barrel_added = True

                elif color not in colors_in_plan:
                    if (barrel.ml_per_barrel > 0 and (num_green_ml + num_red_ml + num_blue_ml + num_dark_ml + barrel.ml_per_barrel <= 10000)
                            and (gold >= barrel.price)):
                        plan.append({"sku": barrel.sku, "quantity": 1}) # Only every buy 1 barrel for now
                        colors_in_plan.add(color)
                        gold -= barrel.price

                # If all colors are already in the plan, stop adding barrels
                if len(colors_in_plan) == 4:
                    break

    return plan








