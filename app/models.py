# app/models.py
from pydantic import BaseModel
from typing import Optional

class Product(BaseModel):
    id: str
    name: str
    price_cents: int
    quantity: int
    category: Optional[str] = "general"
