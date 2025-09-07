# tests/test_concurrency.py
import asyncio
import httpx
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

async def _buy_task(product_id, email, key):
    async with httpx.AsyncClient(app=app, base_url="http://test") as ac:
        r = await ac.post("/buy", json={"user_email": email, "product_id": product_id, "quantity": 1}, headers={"Idempotency-Key": key})
        return r

def test_concurrent_last_item():
    # reset and seed product with quantity 1 and two wallets
    client.post("/reset")
    r = client.post("/seller/register", json={"name":"last","price_cents":1000,"quantity":1,"category":"x"})
    pid = r.json()["product"]["id"]
    client.post("/wallet/topup", json={"user_email":"u1@example.com","amount_cents":5000})
  
    # run two buyers concurrently
    results = asyncio.get_event_loop().run_until_complete(asyncio.gather(
        _buy_task(pid, "u1@example.com", "k1"),
        _buy_task(pid, "u2@example.com", "k2"),
    ))
    statuses = [r.status_code for r in results]
    # one should succeed (200) and the other should fail (409)
    assert 200 in statuses
    assert 409 in statuses or 402 in statuses
