from fastapi import APIRouter
import sqlalchemy
from src import database as db
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    catalog_items = []

    # Fetch the top six potions with the highest quantity and exclude those with quantity of 0
    sql_to_execute = """
        SELECT name, quantity, price, sku, red, green, blue, dark FROM potions 
        WHERE quantity > 0
        ORDER BY quantity DESC 
        LIMIT 6
    """

    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))

        for row in result:
            name, quantity, price, sku, red, green, blue, dark = row
            catalog_items.append({
                "sku": sku,
                "name": name,
                "quantity": quantity,
                "price": price,
                "potion_type": [red, green, blue, dark]
            })

    return catalog_items