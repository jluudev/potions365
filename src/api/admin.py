from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """

    reset_carts = """

        -- Reset cart_items
        DELETE FROM cart_items;
        -- Reset carts
        DELETE FROM carts;
    """

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(reset_carts))
        connection.execute(sqlalchemy.text("TRUNCATE inventory_transactions CASCADE"))
        connection.execute(sqlalchemy.text("TRUNCATE potions_transactions CASCADE"))
        result = connection.execute(sqlalchemy.text("INSERT INTO inventory_transactions DEFAULT VALUES RETURNING id")).first()
        transaction_id = result.id
        connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_entries (transaction_id, change_gold, change_red_ml, change_green_ml, change_blue_ml, change_dark_ml)
            VALUES (:transaction_id, 100, 0, 0, 0, 0)
            """), {"transaction_id": transaction_id})
    return "OK"


