import asyncio
from typing import Dict, Any, List

# This file holds all the in-memory data stores and concurrency locks.

PRODUCTS: Dict[str, Dict[str, Any]] = {}
WALLETS: Dict[str, int] = {}
CARTS: Dict[str, Dict[str, int]] = {}
ORDERS: Dict[str, Dict[str, Any]] = {}
IDEMPOTENCY: Dict[str, Dict[str, Any]] = {}
_LOCKS: Dict[str, asyncio.Lock] = {}

def _get_lock(key: str) -> asyncio.Lock:
    if key not in _LOCKS:
        _LOCKS[key] = asyncio.Lock()
    return _LOCKS[key]