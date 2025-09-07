import asyncio
from sdk.pystore import StoreClient
import requests

async def simulate_purchase(client, email, product_id, qty):
    try:
        client.add_to_cart(email, product_id, qty)
        resp = client.place_order(email)

        if isinstance(resp, dict) and resp.get("status") == "order placed":
            print(f"✅ {email} successfully purchased {qty} units "
                  f"(Order ID: {resp['order_id']}, Total: {resp['total_cents']} cents)")
        else:
            print(f"⚠️  {email} unexpected order response: {resp}")

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 409:
            print(f"❌ {email} order failed: Product already sold out.")
        elif e.response.status_code == 404:
            print(f"❌ {email} order failed: Product not found.")
        else:
            print(f"❌ {email} order failed with error: {e}")
    except Exception as e:
        print(f"❌ {email} unexpected failure: {e}")

async def main():
    c = StoreClient(base_url="http://127.0.0.1:8085")

    # Reset store if available
    try:
        c.reset()
    except Exception:
        pass

    # Register product
    product = c.register_product("Gaming Laptop", 5000, 2, "electronics")["product"]
    product_id = product["id"]
    print(f"\n🖥️  Registered product: {product}")

    # Top up wallets
    c.top_up_wallet("alice@example.com", 10000)
    c.top_up_wallet("bob@example.com", 10000)

    # Run concurrent purchases
    print("\n⚡ Simulating concurrent purchases...")
    await asyncio.gather(
        simulate_purchase(c, "alice@example.com", product_id, 2),
        simulate_purchase(c, "bob@example.com", product_id, 2),
    )

    # Show final state
    print("\n📦 Final product state:", c.get_product(product_id))
    print("👛 Alice wallet:", c.view_wallet("alice@example.com"))
    print("👛 Bob wallet:", c.view_wallet("bob@example.com"))
    print("🧾 Alice orders:", c.list_orders("alice@example.com"))
    print("🧾 Bob orders:", c.list_orders("bob@example.com"))

if __name__ == "__main__":
    asyncio.run(main())
