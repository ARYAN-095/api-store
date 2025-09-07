# tests/test_buy_wallet.py
from fastapi.testclient import TestClient
from app.main import app, PRODUCTS, WALLETS, ORDERS, IDEMPOTENCY

client = TestClient(app)

def reset():
    client.post("/reset")

def test_buy_success_and_wallet_debit():
    reset()
    # create product
    r = client.post("/seller/register", json={"name":"Tst","price_cents":1000,"quantity":5,"category":"x"})
    pid = r.json()["product"]["id"]
    # top up wallet
    client.post("/wallet/topup", json={"user_email":"alice@example.com","amount_cents":5000})
    # buy 2
    r2 = client.post("/buy", json={"user_email":"alice@example.com","product_id":pid,"quantity":2}, headers={"Idempotency-Key":"k1"})
    assert r2.status_code == 200
    body = r2.json()
    assert body["status"] == "order placed"
    # wallet should be debited
    w = client.get("/wallet/alice@example.com").json()
    assert w["balance_cents"] == 5000 - 2000

def test_insufficient_stock_and_funds():
    reset()
    r = client.post("/seller/register", json={"name":"Tst2","price_cents":1000,"quantity":1,"category":"x"})
    pid = r.json()["product"]["id"]
    client.post("/wallet/topup", json={"user_email":"bob@example.com","amount_cents":500})
    # try to buy 2 (stock 1)
    r2 = client.post("/buy", json={"user_email":"bob@example.com","product_id":pid,"quantity":2}, headers={"Idempotency-Key":"k2"})
    assert r2.status_code == 409
    # try to buy 1 but not enough funds (price 1000, bob has 500)
    r3 = client.post("/buy", json={"user_email":"bob@example.com","product_id":pid,"quantity":1}, headers={"Idempotency-Key":"k3"})
    assert r3.status_code == 402
