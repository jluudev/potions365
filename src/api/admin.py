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

    sql_to_execute = """
        -- Reset global inventory
        UPDATE global_inventory
        SET num_green_ml = 0,
            num_red_ml = 0,
            num_blue_ml = 0,
            num_dark_ml = 0,
            gold = 100;

        -- Reset potions inventory
        UPDATE potions
        SET quantity = 0;

        -- Reset carts
        DELETE FROM carts;

        -- Reset cart_items
        DELETE FROM cart_items;
    """

    # Execute the combined SQL statements within a single transaction
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(sql_to_execute))

    return "OK"

