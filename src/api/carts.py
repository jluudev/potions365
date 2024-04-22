from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """
    # with db.engine.begin() as connection:
    #   result = connection.execute(sqlalchemy.text(sql_to_execute))
    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    # with db.engine.begin() as connection:
    #   result = connection.execute(sqlalchemy.text(sql_to_execute))
    print(customers)

    return "OK"

@router.post("/")
def create_cart(new_cart: Customer):
    """ """
    with db.engine.begin() as connection:
        result = connection.execute(
            sqlalchemy.text("INSERT INTO carts (customer_name) VALUES (:customer_name) RETURNING id"),
            {"customer_name": new_cart.customer_name}
        )
        cart_id = result.scalar()
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int

@router.post("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    """ """
    with db.engine.begin() as connection:
        potion_id_result = connection.execute(
            sqlalchemy.text("SELECT id FROM potions WHERE sku = :sku"),
            {"sku": item_sku}
        )
        potion_id_row = potion_id_result.fetchone()
        if potion_id_row:
            potion_id = potion_id_row[0]
        else:
            return {"error": f"No potion found with SKU {item_sku}"}

        # Insert the cart item with the fetched potion_id
        connection.execute(
            sqlalchemy.text("INSERT INTO cart_items (cart_id, potion_id, quantity) VALUES (:cart_id, :potion_id, :quantity)"),
            {"cart_id": cart_id, "potion_id": potion_id, "quantity": cart_item.quantity}
        )
    return {"cart_id": cart_id}

class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    """ """
    with db.engine.begin() as connection:
        # Fetch cart items with their associated potion IDs and quantities
        cart_items_result = connection.execute(
            sqlalchemy.text("SELECT potion_id, quantity FROM cart_items WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        )
        cart_items = cart_items_result.fetchall()

        # Calculate total cost
        total_cost = 0
        for potion_id, quantity in cart_items:
            # Retrieve potion price from the potions table
            potion_price_result = connection.execute(
                sqlalchemy.text("SELECT price FROM potions WHERE id = :potion_id"),
                {"potion_id": potion_id}
            )
            potion_price = potion_price_result.scalar()
            total_cost += quantity * potion_price

        # Deduct gold from global inventory
        connection.execute(
            sqlalchemy.text("UPDATE global_inventory SET gold = gold + :total_cost"),
            {"total_cost": total_cost}
        )
        
        # Subtract potions from global inventory
        for potion_id, quantity in cart_items:
            connection.execute(
                sqlalchemy.text("UPDATE potions SET quantity = quantity - :quantity WHERE id = :potion_id"),
                {"quantity": quantity, "potion_id": potion_id}
            )
        
        # Clear cart items
        connection.execute(
            sqlalchemy.text("DELETE FROM cart_items WHERE cart_id = :cart_id"),
            {"cart_id": cart_id}
        )

        # Remove cart
        connection.execute(
            sqlalchemy.text("DELETE FROM carts WHERE id = :cart_id"),
            {"cart_id": cart_id}
        )
        
        return {"total_potions_bought": sum([quantity for _, quantity in cart_items]), "total_gold_paid": total_cost}

