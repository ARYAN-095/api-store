from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, Dict, Any, List

# Import core logic and data models from other files
from .sdk import (
    seller_register_logic,
    list_products_logic,
    search_product_logic,
    get_product_logic,
    wallet_topup_logic,
    get_wallet_logic,
    cart_add_logic,
    view_cart_logic,
    cart_remove_logic,
    cart_checkout_logic,
    buy_logic,
    list_orders_logic,
    reset_all_logic
)

from .core import (
    ProductIn, WalletTopupIn, BuyRequest, AddToCartIn,
    RemoveFromCartIn
)

app = FastAPI(title="api-store (in-memory demo)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# Seller endpoints
# ---------------------------
@app.post("/seller/register", status_code=201)
async def seller_register(payload: ProductIn):
    return await seller_register_logic(payload)

# ---------------------------
# Product endpoints
# ---------------------------
@app.get("/products")
async def list_products(category: Optional[str] = None, available_only: bool = False):
    return await list_products_logic(category, available_only)

@app.get("/products/search")
async def search_product(name: str = Query(..., min_length=1)):
    return await search_product_logic(name)

@app.get("/products/{product_id}")
async def get_product(product_id: str):
    return await get_product_logic(product_id)

# ---------------------------
# Wallet endpoints
# ---------------------------
@app.post("/wallet/topup")
async def wallet_topup(payload: WalletTopupIn):
    return await wallet_topup_logic(payload)

@app.get("/wallet/{user_email}")
async def get_wallet(user_email: str):
    return await get_wallet_logic(user_email)

# ---------------------------
# Cart endpoints
# ---------------------------
@app.post("/cart/add")
async def cart_add(payload: AddToCartIn):
    return await cart_add_logic(payload)

@app.get("/cart/{user_email}")
async def view_cart(user_email: str):
    return await view_cart_logic(user_email)

@app.post("/cart/remove")
async def cart_remove(payload: RemoveFromCartIn):
    return await cart_remove_logic(payload)

# ---------------------------
# Cart checkout (atomic multi-sku)
# ---------------------------
@app.post("/cart/checkout")
async def cart_checkout(user_email: str, idempotency_key: Optional[str] = Header(None)):
    return await cart_checkout_logic(user_email, idempotency_key)

# ---------------------------
# Buy endpoint (single-product)
# ---------------------------
@app.post("/buy")
async def buy(req: BuyRequest, idempotency_key: Optional[str] = Header(None)):
    return await buy_logic(req, idempotency_key)

# ---------------------------
# Orders
# ---------------------------
@app.get("/orders/{user_email}")
async def list_orders(user_email: str):
    return await list_orders_logic(user_email)

# ---------------------------
# Utility: reset (for tests/demo)
# ---------------------------
@app.post("/reset")
async def reset_all():
    return await reset_all_logic()
