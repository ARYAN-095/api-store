# interactive_cli_autocomplete.py
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.prompt import IntPrompt, Confirm, Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich import box

from prompt_toolkit import prompt
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.styles import Style as PromptStyle

from sdk.pystore import StoreClient
import requests

console = Console()
# c = StoreClient(base_url="http://127.0.0.1:8085")
c = StoreClient(base_url="http://api:8085")


# Global state for status messages and caching
status_message = "Ready"
product_cache: List[Dict[str, Any]] = []
user_cache = set()

# Custom prompt style for prompt_toolkit
custom_style = PromptStyle.from_dict({
    'completion-menu.completion': 'bg:#008888 #ffffff',
    'completion-menu.completion.current': 'bg:#00aaaa #000000',
    'scrollbar.background': 'bg:#88aaaa',
    'scrollbar.button': 'bg:#222222',
})


# ---------------------------
# Small utility to unwrap API responses (sdk returns dict/list or Response objects)
# ---------------------------
def _unwrap_resp(resp: Any) -> Any:
    """
    If resp is a requests/httpx Response, try to decode JSON; else return as-is.
    """
    if resp is None:
        return None
    # requests / httpx response objects have .status_code
    if hasattr(resp, "status_code"):
        try:
            return resp.json()
        except Exception:
            # fallback to textual content
            try:
                return {"error": f"HTTP {resp.status_code}: {resp.text}"}
            except Exception:
                return {"error": f"HTTP {resp.status_code}"}
    # already a Python object
    return resp


# ---------------------------
# Display helpers
# ---------------------------
def show_products(products: List[Dict[str, Any]]):
    if not products:
        console.print("[italic yellow]No products found[/italic yellow]")
        return

    table = Table(
        title="📦 Products Catalog",
        box=box.ROUNDED,
        header_style="bold cyan",
        title_style="bold magenta",
        show_lines=True
    )
    table.add_column("ID", style="dim", width=12)
    table.add_column("Name", style="bold", width=20)
    table.add_column("Price", justify="right", width=10)
    table.add_column("Qty", justify="right", width=8)
    table.add_column("Category", width=15)

    for p in products:
        price_dollars = p.get("price_cents", 0) / 100
        table.add_row(
            p.get("id", "N/A"),
            p.get("name", "N/A"),
            f"${price_dollars:.2f}",
            str(p.get("quantity", 0)),
            p.get("category", "N/A")
        )
    console.print(table)


def show_cart(cart: Dict[str, Any]):
    if not cart:
        console.print("[italic yellow]No cart data[/italic yellow]")
        return

    total_cents = cart.get('total_cents', 0)
    total_dollars = total_cents / 100

    title = Text()
    title.append("🛒 Shopping Cart - ", style="bold")
    title.append(cart.get('user_email', 'Unknown User'), style="bold cyan")
    title.append(f" - Total: ${total_dollars:.2f}", style="bold green")

    items = cart.get("items", [])
    if not items:
        console.print(Panel("Your cart is empty 🛍️", title=title, style="blue"))
        return

    table = Table(box=box.ROUNDED, header_style="bold blue", show_lines=True)
    table.add_column("Product", style="bold", width=30)
    table.add_column("Qty", justify="right", width=8)
    table.add_column("Price", justify="right", width=12)
    table.add_column("Subtotal", justify="right", width=12)

    for it in items:
        if isinstance(it, dict) and "product" in it and it["product"] is not None:
            price_cents = it["product"].get("price_cents", 0)
            price_dollars = price_cents / 100
            line_total_cents = it.get("line_total_cents", price_cents * it.get("quantity", 0))
            table.add_row(
                it["product"].get("name", "Unknown"),
                str(it.get("quantity", 0)),
                f"${price_dollars:.2f}",
                f"${(line_total_cents / 100):.2f}"
            )
        elif isinstance(it, dict) and "product_id" in it:
            table.add_row(
                f"[red]Missing product: {it.get('product_id', 'Unknown')}[/red]",
                str(it.get("quantity", "-")),
                "-",
                "-"
            )
        else:
            table.add_row(str(it)[:30], "-", "-", "-")

    console.print(Panel(table, title=title, border_style="blue"))


def show_wallet(wallet: Dict[str, Any]):
    if not wallet:
        console.print("[italic yellow]No wallet data[/italic yellow]")
        return

    balance_cents = wallet.get('balance_cents', 0)
    balance_dollars = balance_cents / 100

    console.print(
        Panel.fit(
            f"💰 [bold]Balance:[/bold] [green]${balance_dollars:.2f}[/green]",
            title=f"👛 {wallet.get('user_email', 'Unknown User')}'s Wallet",
            border_style="green"
        )
    )


def show_orders(orders: List[Dict[str, Any]], email: str):
    if not orders:
        console.print("[italic yellow]No orders found[/italic yellow]")
        return

    table = Table(
        title=f"📋 Orders for {email}",
        box=box.ROUNDED,
        header_style="bold yellow",
        title_style="bold yellow",
        show_lines=True
    )
    table.add_column("Order ID", style="dim", width=14)
    table.add_column("Contents", width=40)
    table.add_column("Status", width=12)
    table.add_column("Total", justify="right", width=12)
    table.add_column("Items", justify="right", width=8)

    for order in orders:
        # Normalize items to a list of small dicts like {"product_id":..., "quantity":...} or enrich if necessary
        raw_items = order.get("items", None)
        normalized_items: List[Dict[str, Any]] = []

        if isinstance(raw_items, dict):
            # items as mapping product_id -> qty
            for pid, qty in raw_items.items():
                normalized_items.append({"product_id": pid, "quantity": qty})
        elif isinstance(raw_items, list):
            # items might already be list of enriched items from view_cart
            # items could be {'product': {...}, 'quantity': n}
            normalized_items = raw_items.copy()
        else:
            # maybe order is single-product purchase (has product_id)
            if "product_id" in order:
                normalized_items.append({"product_id": order.get("product_id"), "quantity": order.get("quantity", 1)})

        # Build a compact name summary (best-effort product name lookup)
        content_names: List[str] = []
        for it in normalized_items[:3]:
            if isinstance(it, dict) and "product" in it and it["product"]:
                # enriched object from cart
                content_names.append(it["product"].get("name", f"Product {it.get('product_id','?')[:8]}"))
            elif isinstance(it, dict) and "product_id" in it:
                pid = it["product_id"]
                # best-effort get name without heavy UI artifacts
                try:
                    prod = c.get_product(pid)
                    prod_name = prod.get("name", f"Product {pid[:8]}")
                except Exception:
                    prod_name = f"Product {pid[:8]}"
                content_names.append(f"{prod_name} x{it.get('quantity', 1)}")
            else:
                content_names.append(str(it)[:30])

        order_name = ", ".join(content_names) if content_names else "No items"
        if len(normalized_items) > 3:
            order_name += f" +{len(normalized_items) - 3} more"

        total_cents = order.get("total_cents", order.get("total", 0)) or 0
        total_dollars = total_cents / 100
        # items count: sum quantities if possible
        items_count = 0
        for it in normalized_items:
            if isinstance(it, dict):
                items_count += int(it.get("quantity", 1))
            else:
                items_count += 1

        status_style = "green" if order.get("status") in ("placed", "completed") else "yellow"

        table.add_row(
            (order.get("id", order.get("order_id", "N/A"))[:12] + "..."),
            order_name,
            f"[{status_style}]{order.get('status', 'N/A')}[/{status_style}]",
            f"${total_dollars:.2f}",
            str(items_count)
        )

    console.print(table)


def show_status(message: str, is_success: bool = True):
    style = "green" if is_success else "red"
    return Panel.fit(f"[{style}]{message}[/{style}]", title="Status")


# ---------------------------
# API wrapper with enhanced exception handling
# ---------------------------
def try_api(fn, *args, success_msg: Optional[str] = None, **kwargs):
    """
    Calls fn(*args, **kwargs). Shows a spinner while calling.
    Returns the raw result (could be dict/list or Response).
    Catches exceptions and updates status_message.
    """
    global status_message
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Processing...", total=None)
            result = fn(*args, **kwargs)

        if success_msg:
            status_message = success_msg
            console.print(show_status(success_msg, True))
        return result
    except Exception as e:
        status_message = f"Error: {e}"
        console.print(show_status(f"Error: {e}", False))
        return None


# ---------------------------
# Autocompletion helpers
# ---------------------------
def get_product_completer():
    global product_cache
    if not product_cache:
        products = try_api(c.list_products) or []
        product_cache = products

    names = [p.get("name", "") for p in product_cache]
    ids = [p.get("id", "") for p in product_cache]
    return WordCompleter([n for n in (names + ids) if n], ignore_case=True)


def get_user_completer():
    global user_cache
    return WordCompleter(list(user_cache), ignore_case=True)


def update_user_cache(email: str):
    global user_cache
    if email:
        user_cache.add(email)


# ---------------------------
# Layout and Header
# ---------------------------
def create_header():
    header = Table(show_header=False, box=box.ROUNDED)
    header.add_column("left", width=30)
    header.add_column("center", width=40)
    header.add_column("right", width=30)

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    header.add_row(
        "🛍️ PyStore SDK",
        "[bold blue]E-Commerce CLI with Autocomplete[/bold blue]",
        f"[dim]{now}[/dim]"
    )
    return Panel(header, style="bold blue")


# ---------------------------
# Input helpers with autocomplete
# ---------------------------
def prompt_with_autocomplete(message: str, completer=None, default: str = ""):
    return prompt(f"{message} ", completer=completer, style=custom_style, default=default)


def ask_float(message: str, default: float = 10.0) -> float:
    # Friendly float input via Prompt.ask (rich) with validation
    while True:
        raw = Prompt.ask(message, default=str(default))
        try:
            return float(raw)
        except ValueError:
            console.print("[red]Please enter a valid number.[/red]")


# ---------------------------
# Main menu
# ---------------------------
def menu():
    global status_message, product_cache, user_cache

    console.clear()
    console.print(create_header())

    # Preload products for autocomplete
    product_cache = try_api(c.list_products) or []

    while True:
        # Display status
        if status_message:
            console.print(show_status(status_message, "Error" not in status_message))

        # Display menu options
        menu_table = Table.grid(padding=(0, 2))
        menu_table.add_column("Key", style="bold cyan", width=4)
        menu_table.add_column("Option", width=30)
        menu_table.add_column("Key", style="bold cyan", width=4)
        menu_table.add_column("Option", width=30)

        options = [
            ("1", "📦 List products", "7", "🛒 View cart"),
            ("2", "🔍 Search products", "8", "✅ Place order"),
            ("3", "➕ Register product", "9", "💰 Top up wallet"),
            ("4", "ℹ️ Get product by ID", "10", "👛 View wallet"),
            ("5", "🛒 Add to cart", "11", "📋 List orders"),
            ("6", "➖ Remove from cart", "12", "🔄 Reset store"),
            ("", "", "q", "👋 Quit")
        ]

        for row in options:
            menu_table.add_row(*row)

        console.print(Panel(menu_table, title="📋 Menu", border_style="yellow"))

        # Get user choice with autocomplete
        choice = prompt_with_autocomplete(
            "\nChoose an option",
            completer=WordCompleter([str(i) for i in range(1, 13)] + ["q", "quit", "exit"])
        ).strip()

        if choice == "1":
            products = try_api(c.list_products, success_msg="Products loaded successfully")
            if products is not None:
                product_cache = products  # Update cache
                show_products(products)

        elif choice == "2":
            term = prompt_with_autocomplete("Enter search term")
            res = try_api(c.search_products, term, success_msg=f"Search for '{term}' completed")
            if res is not None:
                if isinstance(res, str):
                    console.print(f"[yellow]{res}[/yellow]")
                else:
                    show_products(res)

        elif choice == "3":
            name = prompt_with_autocomplete("Enter product name")
            price = ask_float("💰 Price in dollars", default=10.0)
            price_cents = int(price * 100)
            qty = IntPrompt.ask("📦 Quantity", default=1)
            category = prompt_with_autocomplete("🏷️ Category", default="general")
            resp = try_api(
                c.register_product, name, price_cents, qty, category,
                success_msg=f"Product '{name}' registered successfully"
            )
            if resp:
                console.print(Panel(f"Registered product: [green]{resp['product']['id']}[/green]"))
                product_cache = try_api(c.list_products) or []

        elif choice == "4":
            pid = prompt_with_autocomplete("Enter product ID", completer=get_product_completer())
            resp = try_api(c.get_product, pid, success_msg=f"Product {pid} details loaded")
            if resp:
                show_products([resp])

        elif choice == "5":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)
            pid = prompt_with_autocomplete("Enter product ID", completer=get_product_completer())
            qty = IntPrompt.ask("Enter quantity", default=1)
            resp = try_api(c.add_to_cart, email, pid, qty, success_msg=f"Added {qty} of product {pid} to cart")
            if resp is not None:
                # fetch canonical cart view and show it
                cart_view = try_api(c.view_cart, email)
                if cart_view:
                    show_cart(cart_view)

        elif choice == "6":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)
            pid = prompt_with_autocomplete("Enter product ID", completer=get_product_completer())
            if Confirm.ask("Remove entire item from cart?"):
                resp = try_api(c.remove_from_cart, email, pid, success_msg=f"Product {pid} removed from cart")
            else:
                qty = IntPrompt.ask("Quantity to remove", default=1)
                resp = try_api(c.remove_from_cart, email, pid, qty, success_msg=f"Removed {qty} of product {pid} from cart")
            if resp is not None:
                cart_view = try_api(c.view_cart, email)
                if cart_view:
                    show_cart(cart_view)

        elif choice == "7":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)
            resp = try_api(c.view_cart, email, success_msg=f"Cart loaded for {email}")
            if resp:
                show_cart(resp)

        elif choice == "8":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)

            raw = try_api(c.place_order, email, success_msg=f"Order placed for {email}")
            resp = _unwrap_resp(raw)
            if not resp:
                # try_api already printed error
                continue

            # Success case shape: {'status':'order placed','order_id':..,'total_cents':..}
            if isinstance(resp, dict) and resp.get("status") in ("order placed", "placed"):
                order_id = resp.get("order_id") or resp.get("id") or resp.get("orderId") or "N/A"
                total_cents = resp.get("total_cents") or resp.get("total", 0)
                total_dollars = (total_cents or 0) / 100.0
                console.print(Panel.fit(
                    f"[green]Order placed successfully![/green]\n"
                    f"Order ID: [bold]{order_id}[/bold]\n"
                    f"Total: [bold]${total_dollars:.2f}[/bold]",
                    title="✅ Order Confirmation"
                ))
            else:
                # Could be an error payload such as {'detail': 'insufficient_funds'}
                console.print(Panel.fit(f"[red]Order failed:[/red] {resp}", title="❌ Order Failed"))

        elif choice == "9":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)
            amount = ask_float("Amount in dollars", default=10.0)
            amount_cents = int(amount * 100)
            resp = try_api(c.top_up_wallet, email, amount_cents, success_msg=f"Wallet topped up with ${amount:.2f}")
            if resp:
                show_wallet(resp)

        elif choice == "10":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)
            resp = try_api(c.view_wallet, email, success_msg=f"Wallet loaded for {email}")
            if resp:
                show_wallet(resp)

        elif choice == "11":
            email = prompt_with_autocomplete("Enter user email", completer=get_user_completer())
            update_user_cache(email)

            raw = try_api(c.list_orders, email, success_msg=f"Orders loaded for {email}")
            orders = _unwrap_resp(raw)
            if orders is None:
                continue

            if not isinstance(orders, list) or len(orders) == 0:
                console.print("[italic yellow]No orders found[/italic yellow]")
            else:
                show_orders(orders, email)

        elif choice == "12":
            if Confirm.ask("[red]This will clear all data. Continue?[/red]"):
                resp = try_api(c.reset, success_msg="Store reset successfully")
                console.print(resp)
                # Clear caches after reset
                product_cache = []
                user_cache = set()

        elif choice.lower() in ("q", "quit", "exit"):
            if Confirm.ask("Are you sure you want to quit?"):
                console.print(Panel.fit("[bold green]Thank you for using PyStore! 👋[/bold green]", title="Goodbye"))
                sys.exit(0)

        # Add a separator before next iteration
        console.print()
        console.rule(style="dim")


if __name__ == "__main__":
    try:
        menu()
    except KeyboardInterrupt:
        console.print("\n\n[bold red]Interrupted by user[/bold red]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n\n[bold red]Unexpected error: {e}[/bold red]")
        sys.exit(1)
