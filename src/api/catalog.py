from fastapi import APIRouter
import sqlalchemy
from src import database as db
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    """
    Each unique item combination must have only a single price.
    """
    sql_to_execute = """
        SELECT num_green_potions, num_red_potions, num_blue_potions FROM global_inventory
    """
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        num_green_potions, num_red_potions, num_blue_potions = result.first() if result else (0, 0, 0)

    catalog_items = []

    green_potion_price = 50
    red_potion_price = 50
    blue_potion_price = 50

    # Green
    if num_green_potions != 0:
        catalog_items.append({
            "sku": "GREEN_POTION_0",
            "name": "green potion",
            "quantity": num_green_potions,
            "price": green_potion_price,
            "potion_type": [0, 100, 0, 0]
        })

    # Red
    if num_red_potions != 0:
        catalog_items.append({
            "sku": "RED_POTION_0",
            "name": "red potion",
            "quantity": num_red_potions,
            "price": red_potion_price,
            "potion_type": [100, 0, 0, 0]
        })

    # Blue
    if num_blue_potions != 0:
        catalog_items.append({
            "sku": "BLUE_POTION_0",
            "name": "blue potion",
            "quantity": num_blue_potions,
            "price": blue_potion_price,
            "potion_type": [0, 0, 0, 100]
        })

    return catalog_items