# sdk/pystore.py
import requests
import uuid
import threading
import httpx
from typing import Optional
from rich import print

class StoreClient:
    def __init__(self, base_url: str = "http://localhost:8085", api_key: Optional[str] = None, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.timeout = timeout
        if api_key:
            self.session.headers.update({"Authorization": f"Bearer {api_key}"})

    def reset(self):
        return self.session.post(f"{self.base_url}/reset").json()

    def _make_idempotency_key(self, provided: Optional[str]) -> str:
        return provided if provided else uuid.uuid4().hex

    # Seller: register product
    def register_product(self, name: str, price_cents: int, quantity: int, category: str = "general"):
        r = self.session.post(f"{self.base_url}/seller/register", json={
            "name": name, "price_cents": price_cents, "quantity": quantity, "category": category
        }, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def list_products(self, category: Optional[str] = None, available_only: bool = False):
        params = {}
        if category:
            params["category"] = category
        if available_only:
            params["available_only"] = "true"
        r = self.session.get(f"{self.base_url}/products", params=params, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # Wallet
    def top_up_wallet(self, user_email: str, amount_cents: int):
        r = self.session.post(f"{self.base_url}/wallet/topup", json={"user_email": user_email, "amount_cents": amount_cents}, timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    def view_wallet(self, user_email: str):
        r = self.session.get(f"{self.base_url}/wallet/{user_email}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # Cart
    def add_to_cart(self, user_email: str, product_id: str, quantity: int = 1):
        r = self.session.post(f"{self.base_url}/cart/add", json={
            "user_email": user_email, "product_id": product_id, "quantity": quantity
        }, timeout=self.timeout)
        r.raise_for_status()
        return r.json()
    
    def remove_from_cart(self, user_email: str, product_id: str, quantity: Optional[int] = None):
       payload = {"user_email": user_email, "product_id": product_id}
       if quantity is not None:
          payload["quantity"] = int(quantity)   # ensure int
       r = self.session.post(f"{self.base_url}/cart/remove", json=payload, timeout=self.timeout)

    # if product not in cart FastAPI returns 404 — return the JSON (idempotent behavior)
       if r.status_code == 404:
        # return error body so caller can inspect it (don't raise)
          return r.json()

       r.raise_for_status()
       return r.json()

    def view_cart(self, user_email: str):
        r = self.session.get(f"{self.base_url}/cart/{user_email}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()
    
    

    
 # -----------------------
    # Cart checkout / Place order
    # -----------------------
    def place_order(self, user_email: str, idempotency_key: Optional[str] = None):
        key = self._make_idempotency_key(idempotency_key)
        headers = {"Idempotency-Key": key}
        r = self.session.post(f"{self.base_url}/cart/checkout", params={"user_email": user_email}, headers=headers, timeout=self.timeout)
        return r.json()


    # Direct buy (single product)
    def buy(self, user_email: str, product_id: str, quantity: int = 1, idempotency_key: Optional[str] = None):
        key = self._make_idempotency_key(idempotency_key)
        headers = {"Idempotency-Key": key}
        payload = {"user_email": user_email, "product_id": product_id, "quantity": quantity}
        r = self.session.post(f"{self.base_url}/buy", json=payload, headers=headers, timeout=self.timeout)
        # do not r.raise_for_status() — callers may want to inspect 402/409
        return r

    # # Cart checkout
    # def place_order(self, user_email: str, idempotency_key: Optional[str] = None):
    #     key = self._make_idempotency_key(idempotency_key)
    #     headers = {"Idempotency-Key": key}
    #     r = self.session.post(f"{self.base_url}/cart/checkout", params={"user_email": user_email}, headers=headers, timeout=self.timeout)
    #     return r

    # Async buy (example)
    async def buy_async(self, user_email: str, product_id: str, quantity: int = 1, idempotency_key: Optional[str] = None):
        key = self._make_idempotency_key(idempotency_key)
        headers = {"Idempotency-Key": key}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.base_url}/buy", json={"user_email": user_email, "product_id": product_id, "quantity": quantity}, headers=headers)
            return r

    def search_products(self, name: str):
        r = self.session.get(f"{self.base_url}/products/search", params={"name": name}, timeout=self.timeout)
        try:
           r.raise_for_status()
        except requests.exceptions.HTTPError as e:
           if r.status_code == 404:
              return f"No product found with name '{name}'"
           raise e
        return r.json()
    
    def get_product(self, product_id: str):
        r = self.session.get(f"{self.base_url}/products/{product_id}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()
    
    def list_orders(self, user_email: str):
        r = self.session.get(f"{self.base_url}/orders/{user_email}", timeout=self.timeout)
        r.raise_for_status()
        return r.json()

    # Webhook listener for demos
    def listen_webhook(self, port: int = 9000):
        # Spins up a tiny FastAPI server in a background thread to print incoming webhooks for demos
        from fastapi import FastAPI, Request
        import uvicorn
        app = FastAPI()
        @app.post("/webhook")
        async def hook(req: Request):
            data = await req.json()
            print("[green]Webhook received:[/green]", data)
            return {"status": "ok"}
        def _run():
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")
        t = threading.Thread(target=_run, daemon=True)
        t.start()
        print(f"[cyan]Webhook listener running at http://localhost:{port}/webhook[/cyan]")


if __name__ == "__main__":
    import argparse
    from sdk.pystore import StoreClient

    parser = argparse.ArgumentParser(description="PyStore CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # ---------------------------
    # Product commands
    # ---------------------------
    lp = subparsers.add_parser("list-products", help="List all products")
    lp.add_argument("--category", help="Filter products by category")
    lp.add_argument("--available-only", action="store_true", help="Show only products in stock")

    sp = subparsers.add_parser("search", help="Search for products by name")
    sp.add_argument("--name", required=True, help="Product name to search")

    gp = subparsers.add_parser("get-product", help="Get a product by its ID")
    gp.add_argument("--product-id", required=True, help="ID of the product")

    rp = subparsers.add_parser("register-product", help="Register a new product")
    rp.add_argument("--name", required=True, help="Product name")
    rp.add_argument("--price", type=int, required=True, help="Price in cents")
    rp.add_argument("--quantity", type=int, required=True, help="Quantity available")
    rp.add_argument("--category", default="general", help="Product category")

    # ---------------------------
    # Cart commands
    # ---------------------------
    add = subparsers.add_parser("add-to-cart", help="Add product to cart")
    add.add_argument("--email", required=True, help="User email")
    add.add_argument("--product-id", required=True, help="Product ID")
    add.add_argument("--qty", type=int, required=True, help="Quantity to add")

    rm = subparsers.add_parser("remove-from-cart", help="Remove product from cart")
    rm.add_argument("--email", required=True, help="User email")
    rm.add_argument("--product-id", required=True, help="Product ID")
    rm.add_argument("--qty", type=int, help="Quantity to remove (optional, removes all if not specified)")

    vc = subparsers.add_parser("view-cart", help="View cart contents")
    vc.add_argument("--email", required=True, help="User email")

    # ---------------------------
    # Order commands
    # ---------------------------
    po = subparsers.add_parser("place-order", help="Place order for cart or single product")
    po.add_argument("--email", required=True, help="User email")

    # ---------------------------
    # Wallet commands
    # ---------------------------
    vw = subparsers.add_parser("view-wallet", help="View wallet balance")
    vw.add_argument("--email", required=True, help="User email")

    topup = subparsers.add_parser("topup-wallet", help="Top-up wallet balance")
    topup.add_argument("--email", required=True, help="User email")
    topup.add_argument("--amount", type=int, required=True, help="Amount in cents")
    
    lo = subparsers.add_parser("list-orders")
    lo.add_argument("--email", required=True)
    # ---------------------------
    # Parse and execute
    # ---------------------------
    args = parser.parse_args()
    c = StoreClient(base_url="http://127.0.0.1:8085")
    # c = StoreClient(base_url="http://api:8085")

    if args.command == "list-products":
        print(c.list_products())

    elif args.command == "search":
        print(c.search_products(args.name))

    elif args.command == "register-product":
        print(c.register_product(args.name, args.price, args.quantity, args.category))

    elif args.command == "add-to-cart":
        print(c.add_to_cart(args.email, args.product_id, args.qty))

    elif args.command == "remove-from-cart":
        qty = args.qty if args.qty is not None else None
        print(c.remove_from_cart(args.email, args.product_id, qty))

    elif args.command == "view-cart":
        print(c.view_cart(args.email))

    elif args.command == "place-order":
        print(c.place_order(args.email))

    elif args.command == "view-wallet":
        print(c.view_wallet(args.email))

    elif args.command == "topup-wallet":
        print(c.top_up_wallet(args.email, args.amount))
    elif args.command == "get-product":
        print(c.get_product(args.product_id))
    elif args.command == "list-orders":
        print(c.list_orders(args.email))
