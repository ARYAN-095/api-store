 
const BASE_URL =  'http://localhost:8087';
const CURRENCY_SYMBOL = '₹';

// Centralized message display function
function displayMessage(elementId, message, type = 'info') {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = ''; // Clear previous messages
    const msgDiv = document.createElement('div');
    msgDiv.textContent = message;
    msgDiv.className = `message ${type}`;
    el.appendChild(msgDiv);
}

// -------------------
// Helper Functions
// -------------------

function getUserEmail() {
    return document.getElementById('userEmail').value;
}

function displayResult(elementId, data) {
    const el = document.getElementById(elementId);
    if (!el) return;
    el.innerHTML = '';
    
    const renderObject = (obj) => {
        let detailsHtml = '';
        for (const [key, value] of Object.entries(obj)) {
            let formattedValue = value;
            if (key.includes('price') || key.includes('total') || key.includes('balance')) {
                formattedValue = `${CURRENCY_SYMBOL}${value}`;
            } else if (key === 'quantity' && value === 0) {
                formattedValue = '<span class="out-of-stock">Out of Stock</span>';
            } else if (typeof value === 'object' && value !== null) {
                formattedValue = `<pre>${JSON.stringify(value, null, 2)}</pre>`;
            } else if (value === null) {
                formattedValue = 'N/A';
            }

            detailsHtml += `<li><strong>${key}:</strong> ${formattedValue}</li>`;
        }
        return `<ul>${detailsHtml}</ul>`;
    };

    const createCard = (item, title) => {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `<h3>${title}</h3>${renderObject(item)}`;
        return card;
    };

    if (Array.isArray(data)) {
        if (data.length === 0) {
            el.textContent = 'No results found.';
            return;
        }
        data.forEach(item => {
            let title = 'Result';
            if (item.name) {
                title = item.name;
            } else if (item.user_email) {
                title = `Order ID: ${item.id}`;
            }
            el.appendChild(createCard(item, title));
        });
    } else if (typeof data === 'object' && data !== null) {
        let title = 'Result';
        if (data.name) {
            title = data.name;
        } else if (data.user_email) {
            title = `Order ID: ${data.id}`;
        } else if (data.product_id) {
            title = `Product ID: ${data.product_id}`;
        }
        el.appendChild(createCard(data, title));
    } else {
        el.textContent = String(data);
    }
}

function clearResultsAndMessages() {
    const productResultsEl = document.getElementById('productResults');
    if (productResultsEl) productResultsEl.innerHTML = '';
    
    const productMessagesEl = document.getElementById('productMessages');
    if (productMessagesEl) productMessagesEl.innerHTML = '';
    
    const walletInfoEl = document.getElementById('walletInfo');
    if (walletInfoEl) walletInfoEl.innerHTML = '';
    
    const walletMessagesEl = document.getElementById('walletMessages');
    if (walletMessagesEl) walletMessagesEl.innerHTML = '';
    
    const cartResultsEl = document.getElementById('cartResults');
    if (cartResultsEl) cartResultsEl.innerHTML = '';
    
    const cartMessagesEl = document.getElementById('cartMessages');
    if (cartMessagesEl) cartMessagesEl.innerHTML = '';
    
    const ordersResultsEl = document.getElementById('ordersResults');
    if (ordersResultsEl) ordersResultsEl.innerHTML = '';
    
    const ordersMessagesEl = document.getElementById('ordersMessages');
    if (ordersMessagesEl) ordersMessagesEl.innerHTML = '';
    
    const cartItemsDisplayEl = document.getElementById('cartItemsDisplay');
    if (cartItemsDisplayEl) cartItemsDisplayEl.innerHTML = '';
}

function setButtonLoading(button, isLoading) {
    if (!button) return;
    if (isLoading) {
        button.disabled = true;
        button.textContent = 'Loading...';
    } else {
        button.disabled = false;
        button.textContent = button.getAttribute('data-original-text');
    }
}

// -------------------
// API Call Functions
// -------------------

// Seller/Product Endpoints
async function registerProduct() {
    const btn = document.querySelector('button[onclick="registerProduct()"]');
    setButtonLoading(btn, true);
    displayMessage('productMessages', 'Registering product...', 'info');

    const name = document.getElementById('regName').value;
    const price = parseInt(document.getElementById('regPrice').value);
    const quantity = parseInt(document.getElementById('regQty').value);
    const category = document.getElementById('regCategory').value;

    if (!name || isNaN(price) || isNaN(quantity) || price <= 0 || quantity <= 0) {
        displayMessage('productMessages', 'Please fill all required fields with positive values.', 'error');
        setButtonLoading(btn, false);
        return;
    }

    try {
        const payload = {
            name: name,
            price_cents: price,
            quantity: quantity,
            category: category || "general"
        };
        const response = await fetch(`${BASE_URL}/seller/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        
        if (response.ok) {
            displayResult('productResults', result);
            displayMessage('productMessages', 'Product registered successfully!', 'success');
        } else {
            displayMessage('productMessages', `Error: ${result.detail}`, 'error');
        }

    } catch (error) {
        displayMessage('productMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
        refreshUserData();
    }
}

async function listProducts(filter, event) {
    const btn = event ? event.target : null;
    if (btn) {
        btn.setAttribute('data-original-text', btn.textContent);
        setButtonLoading(btn, true);
    }
    displayMessage('productMessages', 'Fetching products...', 'info');
    
    let url = `${BASE_URL}/products`;
    if (filter === 'available') {
        url += '?available_only=true';
    }

    try {
        const response = await fetch(url);
        const result = await response.json();
        displayResult('productResults', result);
        displayMessage('productMessages', `Products loaded successfully.`, 'success');
    } catch (error) {
        displayMessage('productMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        if (btn) {
            setButtonLoading(btn, false);
        }
    }
}

async function searchProducts() {
    const btn = document.querySelector('button[onclick="searchProducts()"]');
    setButtonLoading(btn, true);
    displayMessage('productMessages', 'Searching products...', 'info');

    const name = document.getElementById('searchName').value;
    if (!name) {
        displayMessage('productMessages', 'Please enter a product name to search.', 'error');
        setButtonLoading(btn, false);
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/products/search?name=${encodeURIComponent(name)}`);
        const result = await response.json();
        displayResult('productResults', result);
        displayMessage('productMessages', `Search for '${name}' completed.`, 'success');
    } catch (error) {
        displayMessage('productMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function getProduct() {
    const btn = document.querySelector('button[onclick="getProduct()"]');
    setButtonLoading(btn, true);
    displayMessage('productMessages', 'Fetching product details...', 'info');

    const id = document.getElementById('getProductId').value;
    if (!id) {
        displayMessage('productMessages', 'Please enter a Product ID.', 'error');
        setButtonLoading(btn, false);
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/products/${id}`);
        const result = await response.json();
        if (response.ok) {
            displayResult('productResults', result);
            displayMessage('productMessages', `Product details for ID '${id}' loaded.`, 'success');
        } else {
            displayMessage('productMessages', `Error: ${result.detail}`, 'error');
        }
    } catch (error) {
        displayMessage('productMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

// Wallet Endpoints
async function viewWallet() {
    const email = getUserEmail();
    const response = await fetch(`${BASE_URL}/wallet/${email}`);
    const result = await response.json();
    document.getElementById('walletInfo').textContent = `Balance: ${CURRENCY_SYMBOL}${result.balance_cents}`;
}

async function topupWallet() {
    const btn = document.querySelector('button[onclick="topupWallet()"]');
    setButtonLoading(btn, true);
    displayMessage('walletMessages', 'Processing top-up...', 'info');

    const email = getUserEmail();
    const amount = parseInt(document.getElementById('topupAmount').value);

    if (!email || isNaN(amount) || amount <= 0) {
        displayMessage('walletMessages', 'Please enter a valid email and positive amount.', 'error');
        setButtonLoading(btn, false);
        return;
    }
    
    try {
        const response = await fetch(`${BASE_URL}/wallet/topup`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_email: email, amount_cents: amount })
        });
        const result = await response.json();

        if (response.ok) {
            displayResult('ordersResults', result);
            displayMessage('walletMessages', `Wallet topped up successfully! New balance: ${CURRENCY_SYMBOL}${result.balance_cents}`, 'success');
            viewWallet();
        } else {
            displayMessage('walletMessages', `Error: ${result.detail}`, 'error');
        }
    } catch (error) {
        displayMessage('walletMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

// Cart Endpoints
async function addToCart() {
    const btn = document.querySelector('button[onclick="addToCart()"]');
    setButtonLoading(btn, true);
    displayMessage('cartMessages', 'Adding to cart...', 'info');

    const email = getUserEmail();
    const productId = document.getElementById('addProductId').value;
    const quantity = parseInt(document.getElementById('addQty').value);

    if (!email || !productId || isNaN(quantity) || quantity <= 0) {
        displayMessage('cartMessages', 'Please enter a valid email, product ID, and positive quantity.', 'error');
        setButtonLoading(btn, false);
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/cart/add`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_email: email, product_id: productId, quantity: quantity })
        });
        const result = await response.json();
        
        if (response.ok) {
            displayResult('cartResults', result);
            displayMessage('cartMessages', `Added to cart successfully!`, 'success');
        } else {
            displayMessage('cartMessages', `Error: ${result.detail}`, 'error');
        }

    } catch (error) {
        displayMessage('cartMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function removeFromCart() {
    const btn = document.querySelector('button[onclick="removeFromCart()"]');
    setButtonLoading(btn, true);
    displayMessage('cartMessages', 'Removing from cart...', 'info');

    const email = getUserEmail();
    const productId = document.getElementById('removeProductId').value;
    const quantity = document.getElementById('removeQty').value;
    
    if (!email || !productId) {
        displayMessage('cartMessages', 'Please enter a valid email and product ID.', 'error');
        setButtonLoading(btn, false);
        return;
    }

    const payload = { user_email: email, product_id: productId };
    if (quantity) {
        payload.quantity = parseInt(quantity);
        if (isNaN(payload.quantity) || payload.quantity <= 0) {
            displayMessage('cartMessages', 'Quantity must be a positive number.', 'error');
            setButtonLoading(btn, false);
            return;
        }
    }

    try {
        const response = await fetch(`${BASE_URL}/cart/remove`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        displayResult('cartResults', result);
        displayMessage('cartMessages', `Product removed from cart successfully!`, 'success');
    } catch (error) {
        displayMessage('cartMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function viewCart() {
    const btn = document.querySelector('button[onclick="viewCart()"]');
    setButtonLoading(btn, true);
    displayMessage('cartMessages', 'Fetching cart...', 'info');

    const email = getUserEmail();
    if (!email) {
        displayMessage('cartMessages', 'Please enter an email to view the cart.', 'error');
        setButtonLoading(btn, false);
        return;
    }
    
    try {
        const response = await fetch(`${BASE_URL}/cart/${email}`);
        const result = await response.json();
        displayResult('cartResults', result);
        displayMessage('cartMessages', 'Cart details loaded successfully.', 'success');
    } catch (error) {
        displayMessage('cartMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

// Order & Utility Endpoints
async function placeOrder() {
    const btn = document.querySelector('button[onclick="placeOrder()"]');
    btn.setAttribute('data-original-text', btn.textContent);
    setButtonLoading(btn, true);
    displayMessage('ordersMessages', 'Processing checkout...', 'info');

    const email = getUserEmail();
    if (!email) {
        displayMessage('ordersMessages', 'Please enter a user email to checkout.', 'error');
        setButtonLoading(btn, false);
        return;
    }
    
    try {
        const idempotencyKey = crypto.randomUUID();
        const response = await fetch(`${BASE_URL}/cart/checkout?user_email=${email}`, {
            method: 'POST',
            headers: { 'Idempotency-Key': idempotencyKey }
        });
        const result = await response.json();
        
        if (response.ok) {
            displayResult('ordersResults', result);
            displayMessage('ordersMessages', `Your order is placed with ID: ${result.id}`, 'success');
        } else {
            displayMessage('ordersMessages', `Order failed: ${result.detail}`, 'error');
        }
    } catch (error) {
        displayMessage('ordersMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
        refreshUserData();
    }
}

async function buyProduct() {
    const btn = document.querySelector('button[onclick="buyProduct()"]');
    btn.setAttribute('data-original-text', btn.textContent);
    setButtonLoading(btn, true);
    displayMessage('ordersMessages', 'Processing purchase...', 'info');

    const email = getUserEmail();
    const productId = document.getElementById('buyProductId').value;
    const quantity = parseInt(document.getElementById('buyQty').value);

    if (!email || !productId || isNaN(quantity) || quantity <= 0) {
        displayMessage('ordersMessages', 'Please enter a valid email, product ID, and positive quantity.', 'error');
        setButtonLoading(btn, false);
        return;
    }
    
    try {
        const idempotencyKey = crypto.randomUUID();
        const payload = { user_email: email, product_id: productId, quantity: quantity };
        const response = await fetch(`${BASE_URL}/buy`, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Idempotency-Key': idempotencyKey
            },
            body: JSON.stringify(payload)
        });
        const result = await response.json();
        
        if (response.ok) {
            displayResult('ordersResults', result);
            displayMessage('ordersMessages', `Purchase successful! Order ID: ${result.id}`, 'success');
        } else {
            displayMessage('ordersMessages', `Purchase failed: ${result.detail}`, 'error');
        }
    } catch (error) {
        displayMessage('ordersMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
        refreshUserData();
    }
}

async function listOrders() {
    const btn = document.querySelector('button[onclick="listOrders()"]');
    btn.setAttribute('data-original-text', btn.textContent);
    setButtonLoading(btn, true);
    displayMessage('ordersMessages', 'Fetching orders...', 'info');

    const email = getUserEmail();
    if (!email) {
        displayMessage('ordersMessages', 'Please enter a user email to list orders.', 'error');
        setButtonLoading(btn, false);
        return;
    }
    
    try {
        const response = await fetch(`${BASE_URL}/orders/${email}`);
        const result = await response.json();
        displayResult('ordersResults', result);
        displayMessage('ordersMessages', 'Orders loaded successfully.', 'success');
    } catch (error) {
        displayMessage('ordersMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function resetStore() {
    const btn = document.querySelector('button[onclick="resetStore()"]');
    btn.setAttribute('data-original-text', btn.textContent);
    setButtonLoading(btn, true);

    const isConfirmed = confirm('Are you sure you want to reset the store? This action is irreversible.');
    if (!isConfirmed) {
        setButtonLoading(btn, false);
        return;
    }

    try {
        const response = await fetch(`${BASE_URL}/reset`, { method: 'POST' });
        const result = await response.json();
        displayMessage('ordersMessages', 'Store has been reset. All data is cleared.', 'success');
        location.reload();
    } catch (error) {
        displayMessage('ordersMessages', `An error occurred: ${error.message}`, 'error');
    } finally {
        setButtonLoading(btn, false);
    }
}

async function refreshUserData() {
    clearResultsAndMessages();
    await viewWallet();
    await viewCart();
    await listProducts('all', null);
    await listOrders();
}

window.onload = refreshUserData;
