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

@router.post("/deliver/{order_id}/")
def post_deliver_barrels(barrels_delivered: list[Barrel]):
    """ """
    with db.engine.begin() as connection:
        total_barrels_cost = 0
        total_ml_per_color = {"red": 0, "green": 0, "blue": 0, "dark": 0}
        
        for barrel in barrels_delivered:
            barrels_cost = barrel.price * barrel.quantity
            total_barrels_cost += barrels_cost
            
            # Calculate the color based on the potion type
            color = "red" if barrel.potion_type == [1, 0, 0, 0] else \
                    "green" if barrel.potion_type == [0, 1, 0, 0] else \
                    "blue" if barrel.potion_type == [0, 0, 1, 0] else \
                    "dark" if barrel.potion_type == [0, 0, 0, 1] else None
            
            if color is not None:
                total_ml_per_color[color] += barrel.ml_per_barrel * barrel.quantity
        
        # Update global_inventory
        transaction_id = connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_transactions (description)
            VALUES (:description)
            RETURNING id
            """), {"description": f"Barreled: {barrels_delivered}"}).first().id
        
        connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_entries
                (change_gold, change_red_ml, change_green_ml, change_blue_ml, change_dark_ml, transaction_id)
            VALUES (:barrels_cost, :num_red_ml, :num_green_ml, :num_blue_ml, :num_dark_ml, :transaction_id)
            """), {"barrels_cost": -total_barrels_cost, 
                   "num_red_ml": total_ml_per_color.get("red", 0),
                   "num_green_ml": total_ml_per_color.get("green", 0),
                   "num_blue_ml": total_ml_per_color.get("blue", 0),
                   "num_dark_ml": total_ml_per_color.get("dark", 0),
                   "transaction_id": transaction_id})
    
    return "OK"



# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    print(wholesale_catalog)
    plan = []
    colors_in_plan = set()  # Set to keep track of colors
    with db.engine.begin() as connection:
        # Fetch global inventory
        global_inventory = connection.execute(sqlalchemy.text("""
            SELECT 
                SUM(change_gold) as gold,
                SUM(change_red_ml) as num_red_ml,
                SUM(change_green_ml) as num_green_ml,
                SUM(change_blue_ml) as num_blue_ml,
                SUM(change_dark_ml) as num_dark_ml
            FROM inventory_entries
        """)).first()
        
        if global_inventory:
            total_gold = global_inventory.gold
            reserved_gold = 0.0 * total_gold  # Always reserve 0% of the total gold
            gold_for_purchase = total_gold - reserved_gold 

            # Reserve gold once I have more than 200 gold
            if total_gold > 200:
                reserved_gold = 0.3 * total_gold
                gold_for_purchase = total_gold - reserved_gold

            num_green_ml = global_inventory.num_green_ml
            num_red_ml = global_inventory.num_red_ml
            num_blue_ml = global_inventory.num_blue_ml
            num_dark_ml = global_inventory.num_dark_ml

            # Filter out MINI barrels
            filtered_catalog = [barrel for barrel in wholesale_catalog if "MINI" not in barrel.sku]

            # Sort the catalog by price per ml
            sorted_catalog = sorted(filtered_catalog, key=lambda barrel: barrel.price / barrel.ml_per_barrel if barrel.ml_per_barrel > 0 else float('inf'))

            dark_barrel_added = False

            for barrel in sorted_catalog:
                color = barrel.sku.split("_")[1].upper()
                # If a dark barrel is available and hasn't been added yet, prioritize it
                if color == "DARK" and not dark_barrel_added:
                    if (barrel.ml_per_barrel > 0 and (num_green_ml + num_red_ml + num_blue_ml + num_dark_ml + barrel.ml_per_barrel <= 25000)
                            and (gold_for_purchase >= barrel.price)):
                        plan.append({"sku": barrel.sku, "quantity": 1}) # Only buy 1 barrel for now
                        colors_in_plan.add(color)
                        gold_for_purchase -= barrel.price
                        num_dark_ml += barrel.ml_per_barrel
                        dark_barrel_added = True

                elif color not in colors_in_plan:
                    if (barrel.ml_per_barrel > 0 and (num_green_ml + num_red_ml + num_blue_ml + num_dark_ml + barrel.ml_per_barrel <= 25000)
                            and (gold_for_purchase >= barrel.price)):
                        plan.append({"sku": barrel.sku, "quantity": 1}) # Only buy 1 barrel for now
                        colors_in_plan.add(color)
                        gold_for_purchase -= barrel.price
                        if color == "RED":
                            num_red_ml += barrel.ml_per_barrel
                        elif color == "GREEN":
                            num_green_ml += barrel.ml_per_barrel
                        elif color == "BLUE":
                            num_blue_ml += barrel.ml_per_barrel
                        elif color == "DARK":
                            num_dark_ml += barrel.ml_per_barrel

                # If all colors are already in the plan, stop adding barrels
                if len(colors_in_plan) == 4:
                    break

    return plan










