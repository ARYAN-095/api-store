import asyncio
import uuid
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Header, Query

# Import from other modules
from .core import (
    ProductIn, WalletTopupIn, BuyRequest, AddToCartIn,
    RemoveFromCartIn, _make_product_dict
)
from .database import (
    PRODUCTS, WALLETS, CARTS, ORDERS,
    IDEMPOTENCY, _get_lock
)

# This file contains the core logic for all API endpoints.

# Seller endpoints
async def seller_register_logic(payload: ProductIn):
    pid = uuid.uuid4().hex
    PRODUCTS[pid] = _make_product_dict(pid, payload)
    return {"product_id": pid, "product": PRODUCTS[pid]}

# Product endpoints
async def list_products_logic(category: Optional[str] = None, available_only: bool = False):
    out = []
    for p in PRODUCTS.values():
        if category and p["category"] != category:
            continue
        if available_only and p["quantity"] <= 0:
            continue
        out.append(p)
    return out

async def search_product_logic(name: str):
    term = name.lower()
    results = [p for p in PRODUCTS.values() if term in p["name"].lower()]
    if not results:
        return []
    return results

async def get_product_logic(product_id: str):
    p = PRODUCTS.get(product_id)
    if not p:
        raise HTTPException(status_code=404, detail="product not found")
    return p

# Wallet endpoints
async def wallet_topup_logic(payload: WalletTopupIn):
    if payload.amount_cents <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")
    
    lock = _get_lock(f"wallet:{payload.user_email}")
    await lock.acquire()

    try:
        balance = WALLETS.get(payload.user_email, 0)
        balance += payload.amount_cents
        WALLETS[payload.user_email] = balance
        return {"user_email": payload.user_email, "balance_cents": balance}
    finally:
        lock.release()

async def get_wallet_logic(user_email: str):
    return {"user_email": user_email, "balance_cents": WALLETS.get(user_email, 0)}

# Cart endpoints
async def cart_add_logic(payload: AddToCartIn):
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be > 0")
    if payload.product_id not in PRODUCTS:
        raise HTTPException(status_code=404, detail="product not found")
    cart = CARTS.setdefault(payload.user_email, {})
    cart[payload.product_id] = cart.get(payload.product_id, 0) + payload.quantity
    return {"user_email": payload.user_email, "cart": cart}

async def view_cart_logic(user_email: str):
    cart = CARTS.get(user_email, {})
    items = []
    total = 0
    for pid, qty in cart.items():
        prod = PRODUCTS.get(pid)
        if not prod:
            items.append({"product_id": pid, "available": False, "quantity_requested": qty})
            continue
        line = prod["price_cents"] * qty
        total += line
        items.append({"product": prod, "quantity": qty, "line_total_cents": line})
    return {"user_email": user_email, "items": items, "total_cents": total}

async def cart_remove_logic(payload: RemoveFromCartIn):
    cart = CARTS.setdefault(payload.user_email, {})
    if payload.product_id not in cart:
        return {"user_email": payload.user_email, "cart": cart}

    qty_to_remove = payload.quantity
    if qty_to_remove is not None:
        try:
            qty_to_remove = int(qty_to_remove)
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="quantity must be an integer > 0")
        if qty_to_remove <= 0:
            raise HTTPException(status_code=400, detail="quantity must be > 0")

    current_qty = cart[payload.product_id]
    if qty_to_remove is None or qty_to_remove >= current_qty:
        del cart[payload.product_id]
    else:
        cart[payload.product_id] = current_qty - qty_to_remove

    return {"user_email": payload.user_email, "cart": cart}

# Cart checkout (atomic multi-sku)
async def cart_checkout_logic(user_email: str, idempotency_key: Optional[str]):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    prev = IDEMPOTENCY.get(idempotency_key)
    if prev is not None:
        return prev

    cart = CARTS.get(user_email, {})
    if not cart:
        raise HTTPException(status_code=400, detail="cart empty")

    product_keys = [f"product:{pid}" for pid in cart.keys()]
    keys_sorted = sorted(product_keys + [f"wallet:{user_email}"])
    locks = [_get_lock(k) for k in keys_sorted]
    for l in locks:
        await l.acquire()

    try:
        total = 0
        items = []
        for pid, qty in cart.items():
            prod = PRODUCTS.get(pid)
            if not prod:
                raise HTTPException(status_code=404, detail=f"product_not_found:{pid}")
            if qty <= 0:
                raise HTTPException(status_code=400, detail="invalid quantity in cart")
            if prod["quantity"] < qty:
                raise HTTPException(status_code=409, detail=f"insufficient_stock:{pid}")
            line_total = prod["price_cents"] * qty
            total += line_total
            items.append({
                "product_id": pid,
                "name": prod["name"],
                "quantity": qty,
                "line_total_cents": line_total
            })

        balance = WALLETS.get(user_email, 0)
        if balance < total:
            raise HTTPException(status_code=402, detail="insufficient_funds")

        for pid, qty in cart.items():
            PRODUCTS[pid]["quantity"] -= qty
        WALLETS[user_email] = balance - total

        order_id = uuid.uuid4().hex
        order = {
            "id": order_id,
            "user_email": user_email,
            "items": items,
            "total_cents": total,
            "status": "placed"
        }
        ORDERS[order_id] = order
        CARTS[user_email] = {}

        IDEMPOTENCY[idempotency_key] = order
        return order
    finally:
        for l in reversed(locks):
            try:
                l.release()
            except RuntimeError:
                pass

# Buy endpoint (single-product)
async def buy_logic(req: BuyRequest, idempotency_key: Optional[str]):
    if not idempotency_key:
        raise HTTPException(status_code=400, detail="Idempotency-Key header required")
    prev = IDEMPOTENCY.get(idempotency_key)
    if prev is not None:
        return prev

    if req.quantity <= 0:
        raise HTTPException(status_code=400, detail="quantity must be > 0")

    prod = PRODUCTS.get(req.product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="product not found")

    keys = [f"product:{req.product_id}", f"wallet:{req.user_email}"]
    locks = [_get_lock(k) for k in sorted(keys)]
    for l in locks:
        await l.acquire()

    try:
        if prod["quantity"] < req.quantity:
            raise HTTPException(status_code=409, detail="insufficient_stock")

        total = prod["price_cents"] * req.quantity
        balance = WALLETS.get(req.user_email, 0)
        if balance < total:
            raise HTTPException(status_code=402, detail="insufficient_funds")

        prod["quantity"] -= req.quantity
        WALLETS[req.user_email] = balance - total

        order_id = uuid.uuid4().hex
        order = {
            "id": order_id,
            "user_email": req.user_email,
            "items": [{
                "product_id": req.product_id,
                "name": prod["name"],
                "quantity": req.quantity,
                "line_total_cents": total
            }],
            "total_cents": total,
            "status": "placed"
        }
        ORDERS[order_id] = order

        IDEMPOTENCY[idempotency_key] = order
        return order
    finally:
        for l in reversed(locks):
            try:
                l.release()
            except RuntimeError:
                pass

# Orders
async def list_orders_logic(user_email: str):
    out = [o for o in ORDERS.values() if o.get("user_email") == user_email]
    return out

# Utility: reset (for tests/demo)
async def reset_all_logic():
    PRODUCTS.clear()
    WALLETS.clear()
    CARTS.clear()
    ORDERS.clear()
    IDEMPOTENCY.clear()
    _LOCKS.clear()
    return {"status": "reset"}
