from fastapi import APIRouter
import sqlalchemy
from src import database as db
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.connect() as connection:
        # Fetch all available potion types
        sql_to_execute = sqlalchemy.text(
            """
            SELECT potions.sku, potions.price, potions.red AS red, potions.green AS green, potions.blue AS blue, potions.dark AS dark, COALESCE(SUM(pe.change), 0) AS quantity
            FROM potions
            LEFT JOIN potions_entries AS pe ON pe.potion_sku = potions.sku
            GROUP BY potions.sku, potions.price, potions.red, potions.green, potions.blue, potions.dark
            ORDER BY quantity DESC
            """
        )
        potion_inventory = connection.execute(sql_to_execute).fetchall()

        catalog_items = []

        for potion in potion_inventory:
            if potion.quantity > 0:
                catalog_items.append({
                    "sku": potion.sku,
                    "name": potion.sku,
                    "quantity": potion.quantity,
                    "price": potion.price,
                    "potion_type": [potion.red, potion.green, potion.blue, potion.dark],
                })

        if len(catalog_items) > 6:
            catalog_items = catalog_items[:6]

    return catalog_items


