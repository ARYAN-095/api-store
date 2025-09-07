# PyStore — In-memory demo API + Python SDK
https://img.shields.io/badge/PyStore-FastAPI%2520%252B%2520SDK-blue

A lightweight, in-memory FastAPI e-commerce demo with a fully-featured Python SDK. Perfect for demonstrating API design, concurrency handling, idempotent operations, and client library development.

# ✨ Features
- RESTful API with FastAPI

- Python SDK with synchronous and asynchronous clients

- Interactive TUI with autocomplete

- Command-line interface

- Concurrency-safe operations with locking

- Idempotent purchases with idempotency keys

- Demo scripts for sequential and concurrent scenarios

- Static frontend with nginx serving

- Docker containerization for easy deployment


# 🚀 Quick Start

## Local Development

```
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Start the API server
uvicorn app.main:app --host 0.0.0.0 --port 8085 --reload
```

### Access the interactive API documentation:

- Swagger UI: http://localhost:8085/docs

- ReDoc: http://localhost:8085/redoc


# Docker Deployment

```
# Build and start all services
docker compose up --build

# Run in background
docker compose up -d --build

# Run CLI interactively
docker compose run --rm cli
```



# 📚 API Overview

```  
Endpoint	       Method	       Description
/seller/register	POST	Register a new product
/products	        GET	    List all products (filterable)
/products/search	GET	    Search products by name
/products/{id}	    GET	    Get specific product
/wallet/topup	    POST	Add funds to user wallet
/wallet/{email}	    GET	    Check wallet balance
/cart/add	        POST	Add item to cart
/cart/remove	    POST	Remove item from cart
/cart/{email}	    GET	    View user's cart
/cart/checkout	    POST	Checkout cart (idempotent)
/buy	            POST	Direct purchase (idempotent)
/orders/{email}	    GET	    List user orders
/order/refund	    POST	Refund an order
/reset	            POST	Reset all data (for testing)
```

# 🐍 Python SDK Usage

## Basic Setup
```
from sdk.pystore import StoreClient

# Initialize client
client = StoreClient("http://localhost:8085")
```

## Common Operations
```
# Register a product
product = client.register_product("Laptop", 150000, 5, "electronics")
product_id = product["product"]["id"]

# Top up wallet
client.top_up_wallet("alice@example.com", 100000)

# Add to cart and checkout
client.add_to_cart("alice@example.com", product_id, 2)
order = client.place_order("alice@example.com")
```

## Handling Purchase Responses
```
response = client.buy("bob@example.com", product_id, 1)

if response.status_code == 200:
    print("Purchase successful!", response.json())
elif response.status_code == 402:
    print("Insufficient funds")
elif response.status_code == 409:
    print("Insufficient stock")
else:
    response.raise_for_status()
```

## Async Operations
```
import asyncio

async def async_purchase():
    response = await client.buy_async("charlie@example.com", product_id, 1)
    print(f"Status: {response.status_code}")
    print(await response.aread())

asyncio.run(async_purchase())
```

# 🖥️ Command Line Interface

## Simple CLI Commands
```
# List all products
python -m sdk.pystore list-products

# Register a new product
python -m sdk.pystore register-product --name "Smartphone" --price 80000 --quantity 10

# Add to cart and checkout
python -m sdk.pystore add-to-cart --email user@example.com --product-id 123 --qty 2
python -m sdk.pystore place-order --email user@example.com
```

## Interactive TUI
```
# Launch interactive interface with autocomplete
python interactive_cli_autocomplete.py
```

# 🧪 Demo Scripts

## Sequential Demo
```
python demo.py
```
Shows a complete workflow: reset → register products → top up wallets → add to cart → checkout → show results.

## Concurrent Demo
```
python demo_concurrent.py
```
Demonstrates concurrency handling with multiple users attempting to purchase limited stock simultaneously.


#🧰 Testing
Run the test suite:
```
# All tests
pytest

# Specific test file
pytest tests/test_concurrency.py

# With verbose output
pytest -v
```

# 🌐 Frontend


The static frontend is served at http://localhost:8080 when using Docker Compose.

For development, you can also open api-store-frontend/index.html directly in a browser.

# 🔒 Concurrency & Idempotency
PyStore implements robust concurrency control:

- Resource locking: Products and wallets are locked during transactions

- Idempotency keys: Prevent duplicate operations when requests are retried

- Atomic operations: Ensure data consistency during concurrent access

Example idempotency usage:
```
import uuid

idempotency_key = str(uuid.uuid4())
response = client.buy("user@example.com", product_id, 1, idempotency_key)

# Subsequent calls with same key return the same result
response2 = client.buy("user@example.com", product_id, 1, idempotency_key)
assert response.json() == response2.json()
```

# 🐛 Troubleshooting

## Common Issues
### 1. Connection refused in Docker

    - Ensure containers are running: docker compose ps

    - Check logs: docker compose logs api

### 2. Frontend can't connect to API

    - Verify API is running on port 8085

    - Check CORS settings if accessing from different origin

### 3. Idempotency key conflicts

    - Use unique keys for each distinct operation

    - Reuse keys only for retrying the exact same operation
 

# 🔧 Extending the SDK
The SDK is designed to be easily extensible:

## Adding Custom Methods
```
class EnhancedStoreClient(StoreClient):
    def purchase_with_retry(self, user_email, product_id, quantity, max_retries=3):
        for attempt in range(max_retries):
            try:
                return self.buy(user_email, product_id, quantity)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
```

## Adding Typed Responses
```
from pydantic import BaseModel

class Product(BaseModel):
    id: str
    name: str
    price_cents: int
    quantity: int
    category: str

def get_product_typed(self, product_id: str) -> Product:
    response = self.get_product(product_id)
    return Product(**response)
```

# 📋 Demo Flow for Presentations

- 1. Start the API: uvicorn app.main:app --reload

- 2. Register products: python -m sdk.pystore register-product --name "Laptop" --price 150000 --quantity 3

- 3. Fund wallet: python -m sdk.pystore topup-wallet --email alice@example.com --amount 100000

- 4. Add to cart: python -m sdk.pystore add-to-cart --email alice@example.com --product-id <id> --qty 2

- 5. Checkout: python -m sdk.pystore place-order --email alice@example.com

- 6. Show results: python -m sdk.pystore view-wallet --email alice@example.com and python -m sdk.pystore list-orders --email alice@example.com

- 7. Demonstrate concurrency: python demo_concurrent.py

# 📝 License
MIT License - feel free to use this project for learning and development purposes.

# 🤝 Contributing
Contributions are welcome! Please feel free to submit a Pull Request.



###    Happy coding! For questions or support, please open an issue in the repository.

