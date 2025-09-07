from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ProductIn(BaseModel):
    name: str
    price_cents: int
    quantity: int
    category: Optional[str] = "general"

class WalletTopupIn(BaseModel):
    user_email: str
    amount_cents: int

class BuyRequest(BaseModel):
    user_email: str
    product_id: str
    quantity: int

class AddToCartIn(BaseModel):
    user_email: str
    product_id: str
    quantity: int = 1

class RemoveFromCartIn(BaseModel):
    user_email: str
    product_id: str
    quantity: Optional[int] = None

def _make_product_dict(product_id: str, p: ProductIn) -> Dict[str, Any]:
    return {
        "id": product_id,
        "name": p.name,
        "price_cents": p.price_cents,
        "quantity": p.quantity,
        "category": p.category
    }
