#!/usr/bin/env python
import uuid
from sdk.pystore import StoreClient

def main():
    c = StoreClient(base_url="http://127.0.0.1:8085")

    # -----------------------------
    # Reset everything for demo
    # -----------------------------
    print("Resetting store...")
    c.session.post(f"{c.base_url}/reset")
    
    # -----------------------------
    # Register products
    # -----------------------------
    print("\nRegistering products...")
    prod1 = c.register_product("Laptop", 1500, 3, "electronics")
    prod2 = c.register_product("Mouse", 500, 10, "electronics")
    print(prod1)
    print(prod2)

    # -----------------------------
    # List products
    # -----------------------------
    print("\nListing products...")
    print(c.list_products())

    # -----------------------------
    # Search product
    # -----------------------------
    print("\nSearching for 'Laptop'...")
    print(c.search_products("Laptop"))

    # -----------------------------
    # Wallet top-up
    # -----------------------------
    user_email = "alice@example.com"
    print(f"\nTopping up wallet for {user_email}...")
    print(c.top_up_wallet(user_email, 10000))

    # -----------------------------
    # Add products to cart
    # -----------------------------
    print("\nAdding products to cart...")
    print(c.add_to_cart(user_email, prod1["product_id"], 1))
    print(c.add_to_cart(user_email, prod2["product_id"], 2))

    # -----------------------------
    # View cart
    # -----------------------------
    print("\nViewing cart...")
    print(c.view_cart(user_email))

    # -----------------------------
    # Place order
    # -----------------------------
    print("\nPlacing order...")
    # Using a deterministic idempotency key for demo
    idempotency_key = str(uuid.uuid4())
    print(c.place_order(user_email, idempotency_key))

    # -----------------------------
    # View wallet after order
    # -----------------------------
    print("\nViewing wallet after order...")
    print(c.view_wallet(user_email))

    # -----------------------------
    # List orders
    # -----------------------------
    print("\nListing all orders...")
    print(c.list_orders(user_email))

if __name__ == "__main__":
    main()
