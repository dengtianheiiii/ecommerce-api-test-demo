"""A minimal in-memory Commerce API used only for local test demonstrations."""

from __future__ import annotations

import json
import threading
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from typing import Any
from urllib.parse import parse_qs, urlparse


class Store:
    def __init__(self) -> None:
        self.lock = threading.Lock()
        self.products = {
            1: {"id": 1, "name": "Mechanical Keyboard", "price": 299.0, "stock": 5},
            2: {"id": 2, "name": "Wireless Mouse", "price": 159.0, "stock": 8},
            3: {"id": 3, "name": "USB-C Cable", "price": 39.0, "stock": 20},
        }
        self.carts: dict[str, dict[int, int]] = {}
        self.orders: dict[str, dict[str, Any]] = {}
        self.order_numbers = count(1001)

    def reset(self) -> None:
        self.__init__()


STORE = Store()
TOKEN = "demo-token"


def reset_store() -> None:
    """Reset state between test cases."""
    STORE.reset()


class CommerceRequestHandler(BaseHTTPRequestHandler):
    server_version = "CommerceDemo/1.0"

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any] | None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            return json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._send_json(HTTPStatus.BAD_REQUEST, {"message": "invalid JSON body"})
            return None

    def _is_authorized(self) -> bool:
        if self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self._send_json(HTTPStatus.UNAUTHORIZED, {"message": "authentication required"})
            return False
        return True

    @staticmethod
    def _cart_payload() -> dict[str, Any]:
        cart = STORE.carts.get(TOKEN, {})
        items = []
        total = 0.0
        for product_id, quantity in cart.items():
            product = STORE.products[product_id]
            subtotal = round(product["price"] * quantity, 2)
            total += subtotal
            items.append({"product_id": product_id, "name": product["name"], "quantity": quantity, "subtotal": subtotal})
        return {"items": items, "total": round(total, 2)}

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send_json(HTTPStatus.OK, {"status": "ok"})
            return
        if parsed.path == "/api/products":
            keyword = parse_qs(parsed.query).get("keyword", [""])[0].lower()
            products = [product for product in STORE.products.values() if keyword in product["name"].lower()]
            self._send_json(HTTPStatus.OK, {"items": products, "total": len(products)})
            return
        if parsed.path == "/api/cart":
            if self._is_authorized():
                self._send_json(HTTPStatus.OK, self._cart_payload())
            return
        if parsed.path.startswith("/api/orders/"):
            if not self._is_authorized():
                return
            order_id = parsed.path.rsplit("/", 1)[-1]
            order = STORE.orders.get(order_id)
            if order is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"message": "order not found"})
            else:
                self._send_json(HTTPStatus.OK, order)
            return
        self._send_json(HTTPStatus.NOT_FOUND, {"message": "route not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/login":
            body = self._read_json()
            if body is None:
                return
            if body.get("username") == "tester" and body.get("password") == "Passw0rd!":
                self._send_json(HTTPStatus.OK, {"token": TOKEN, "user": {"id": 1, "username": "tester"}})
            else:
                self._send_json(HTTPStatus.UNAUTHORIZED, {"message": "invalid username or password"})
            return

        if self.path == "/api/cart":
            if not self._is_authorized():
                return
            body = self._read_json()
            if body is None:
                return
            product_id, quantity = body.get("product_id"), body.get("quantity")
            if not isinstance(product_id, int) or not isinstance(quantity, int) or quantity <= 0:
                self._send_json(HTTPStatus.BAD_REQUEST, {"message": "product_id and positive integer quantity are required"})
                return
            product = STORE.products.get(product_id)
            if product is None:
                self._send_json(HTTPStatus.NOT_FOUND, {"message": "product not found"})
                return
            if quantity > product["stock"]:
                self._send_json(HTTPStatus.BAD_REQUEST, {"message": "insufficient stock"})
                return
            STORE.carts.setdefault(TOKEN, {})[product_id] = quantity
            self._send_json(HTTPStatus.CREATED, self._cart_payload())
            return

        if self.path == "/api/orders":
            if not self._is_authorized():
                return
            cart = STORE.carts.get(TOKEN, {})
            if not cart:
                self._send_json(HTTPStatus.BAD_REQUEST, {"message": "cart is empty"})
                return
            with STORE.lock:
                for product_id, quantity in cart.items():
                    if quantity > STORE.products[product_id]["stock"]:
                        self._send_json(HTTPStatus.BAD_REQUEST, {"message": "insufficient stock"})
                        return
                order_id = f"ORD-{next(STORE.order_numbers)}"
                payload = self._cart_payload()
                for product_id, quantity in cart.items():
                    STORE.products[product_id]["stock"] -= quantity
                order = {"order_id": order_id, "status": "PENDING_PAYMENT", **payload}
                STORE.orders[order_id] = order
                STORE.carts[TOKEN] = {}
            self._send_json(HTTPStatus.CREATED, order)
            return

        self._send_json(HTTPStatus.NOT_FOUND, {"message": "route not found"})

    def do_PATCH(self) -> None:  # noqa: N802
        if not self.path.startswith("/api/cart/"):
            self._send_json(HTTPStatus.NOT_FOUND, {"message": "route not found"})
            return
        if not self._is_authorized():
            return
        body = self._read_json()
        if body is None:
            return
        try:
            product_id = int(self.path.rsplit("/", 1)[-1])
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"message": "invalid product id"})
            return
        quantity = body.get("quantity")
        cart = STORE.carts.get(TOKEN, {})
        product = STORE.products.get(product_id)
        if not isinstance(quantity, int) or quantity <= 0:
            self._send_json(HTTPStatus.BAD_REQUEST, {"message": "quantity must be a positive integer"})
        elif product_id not in cart or product is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"message": "cart item not found"})
        elif quantity > product["stock"]:
            self._send_json(HTTPStatus.BAD_REQUEST, {"message": "insufficient stock"})
        else:
            cart[product_id] = quantity
            self._send_json(HTTPStatus.OK, self._cart_payload())

    def do_DELETE(self) -> None:  # noqa: N802
        if not self.path.startswith("/api/cart/"):
            self._send_json(HTTPStatus.NOT_FOUND, {"message": "route not found"})
            return
        if not self._is_authorized():
            return
        try:
            product_id = int(self.path.rsplit("/", 1)[-1])
        except ValueError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"message": "invalid product id"})
            return
        cart = STORE.carts.get(TOKEN, {})
        if product_id not in cart:
            self._send_json(HTTPStatus.NOT_FOUND, {"message": "cart item not found"})
            return
        del cart[product_id]
        self._send_json(HTTPStatus.NO_CONTENT, {})


def create_server(host: str = "127.0.0.1", port: int = 0) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, port), CommerceRequestHandler)


if __name__ == "__main__":
    server = create_server(port=8000)
    print("Mock Commerce API listening on http://127.0.0.1:8000")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
    finally:
        server.server_close()
