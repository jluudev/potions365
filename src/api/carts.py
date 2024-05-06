from fastapi import APIRouter, Depends, Request, HTTPException
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
    search_page: str = "0",
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
    try:
        current = int(search_page)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid search_page, it must be an integer.")

    filter_list = []
    if customer_name:
        filter_list.append("c.customer_name ILIKE :customer_name")
    if potion_sku:
        filter_list.append("p.sku ILIKE :potion_sku")
    filter = " AND ".join(filter_list)
    filter = f"WHERE {filter}" if filter_list else ""

    sql = f"""
        SELECT
            ci.id AS line_item_id,
            CONCAT(ci.quantity, ' ', p.sku, ' potion') AS item_sku,
            c.customer_name,
            (ci.quantity * p.price) AS line_item_total,
            it.created_at AS timestamp
        FROM
            cart_items ci
        JOIN
            carts c ON ci.cart_id = c.id
        JOIN
            potions p ON ci.potion_id = p.id
        JOIN
            inventory_transactions it ON c.inventory_transaction_id = it.id
        {filter}
        ORDER BY
            {sort_col.value} {sort_order.value}
        LIMIT 5
        OFFSET :offset
    """

    params = {
        'customer_name': f"%{customer_name}%" if customer_name else None,
        'potion_sku': f"%{potion_sku}%" if potion_sku else None,
        'offset': current
    }

    with db.engine.begin() as connection:
        results = connection.execute(sqlalchemy.text(sql), params).fetchall()

    formatted_results = [{
        "line_item_id": result[0],
        "item_sku": result[1],
        "customer_name": result[2],
        "line_item_total": float(result[3]),
        "timestamp": result[4].isoformat() if result[4] else None
    } for result in results]

    next_page = current + 5
    next = "" if len(results) < 5 else str(next_page)
    previous = "" if current <= 0 else str(current - 5)

    return {
        "previous": previous,
        "next": next,
        "results": formatted_results
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
        total_potions_bought = 0
        total_gold_paid = 0

        # Insert a new inventory transaction
        global_transaction_id = connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_transactions DEFAULT VALUES
            RETURNING id
        """)).scalar()

        connection.execute(sqlalchemy.text("""
            UPDATE carts
            SET payment = :payment, inventory_transaction_id = :global_transaction_id
            WHERE id = :cart_id
        """), {"payment": cart_checkout.payment, "global_transaction_id": global_transaction_id, "cart_id": cart_id})

        cart_items_result = connection.execute(sqlalchemy.text("""
            SELECT potion_id, quantity
            FROM cart_items
            WHERE cart_id = :cart_id
        """), {"cart_id": cart_id})

        cart_items = cart_items_result.fetchall()

        for cart_item in cart_items:
            potion_id, quantity = cart_item

            potion_info = connection.execute(sqlalchemy.text("""
                SELECT price, sku
                FROM potions
                WHERE id = :potion_id
            """), {"potion_id": potion_id}).first()

            if potion_info:
                potion_price = potion_info.price
                potion_sku = potion_info.sku

                total_gold_paid += quantity * potion_price

                total_potions_bought += quantity

                # Insert potion transaction entry
                potion_transaction_id = connection.execute(sqlalchemy.text("""
                    INSERT INTO potions_transactions (description)
                    VALUES (:description)
                    RETURNING id
                """), {"description": f"sold {quantity} {potion_sku}"}).scalar()

                # Insert entry in potions_entries table
                connection.execute(sqlalchemy.text("""
                    INSERT INTO potions_entries (potion_sku, change, transaction_id)
                    VALUES (:potion_id, :change, :potion_transaction_id)
                """), {"potion_id": potion_sku, "change": -quantity, "potion_transaction_id": potion_transaction_id})

        # Update inventory transaction description
        connection.execute(sqlalchemy.text("""
            UPDATE inventory_transactions
            SET description = :description
            WHERE id = :transaction_id
        """), {"description": f"sold {total_potions_bought} potions", "transaction_id": global_transaction_id})

        # Insert global inventory entry for gold deduction
        connection.execute(sqlalchemy.text("""
            INSERT INTO inventory_entries (change_gold, transaction_id)
            VALUES (:total_gold_paid, :transaction_id)
        """), {"total_gold_paid": total_gold_paid, "transaction_id": global_transaction_id})

    return {"total_potions_bought": total_potions_bought, "total_gold_paid": total_gold_paid}


