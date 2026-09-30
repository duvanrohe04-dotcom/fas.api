"""Tests for the order endpoints, the kitchen board and stock movements."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import AsyncClient

from app.tests.conftest import API_PREFIX, auth_header


async def _category(
    client: AsyncClient, headers: dict[str, str], name: str = "Cafés"
) -> dict[str, object]:
    """Create a category to hang products from."""
    response = await client.post(f"{API_PREFIX}/categories", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


async def _product(
    client: AsyncClient,
    headers: dict[str, str],
    category_id: int,
    *,
    name: str = "Espresso",
    price: str = "2.50",
    stock: int = 10,
    low_stock_threshold: int = 2,
) -> dict[str, object]:
    """Create a product with a known price and stock."""
    response = await client.post(
        f"{API_PREFIX}/products",
        json={
            "name": name,
            "price": price,
            "category_id": category_id,
            "stock": stock,
            "low_stock_threshold": low_stock_threshold,
        },
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


async def _table(
    client: AsyncClient, headers: dict[str, str], number: int = 1
) -> dict[str, object]:
    """Create a dining table."""
    response = await client.post(
        f"{API_PREFIX}/tables",
        json={"number": number, "name": f"Mesa {number}"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


async def _order(
    client: AsyncClient,
    headers: dict[str, str],
    product_id: int,
    *,
    quantity: int = 2,
    **extra: object,
) -> dict[str, object]:
    """Create an order with a single line."""
    payload: dict[str, object] = {"items": [{"product_id": product_id, "quantity": quantity}]}
    payload.update(extra)
    response = await client.post(f"{API_PREFIX}/orders", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


@pytest.fixture
async def catalog(client: AsyncClient, admin_token: str) -> AsyncGenerator[dict[str, object], None]:
    """Provide a category with two products plus the admin authorization header."""
    headers = auth_header(admin_token)
    category = await _category(client, headers)
    category_id = int(category["id"])
    espresso = await _product(client, headers, category_id, name="Espresso", price="2.00", stock=10)
    toast = await _product(client, headers, category_id, name="Tostada", price="3.50", stock=10)
    return {
        "headers": headers,
        "category_id": category_id,
        "espresso_id": espresso["id"],
        "toast_id": toast["id"],
    }


@pytest.fixture
async def table(client: AsyncClient, catalog: dict[str, object]) -> dict[str, object]:
    """Provide a dining table registered by the admin."""
    headers = catalog["headers"]
    assert isinstance(headers, dict)
    return await _table(client, headers)


async def test_create_order_computes_totals_and_reserves_stock(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object], table: dict[str, object]
) -> None:
    """The server calculates the totals and decreases the stock."""
    headers = auth_header(cashier_token)
    espresso_id = int(catalog["espresso_id"])

    order = await _order(
        client,
        headers,
        espresso_id,
        quantity=3,
        table_id=table["id"],
        tax="0.50",
        notes="para llevar",
    )

    assert order["code"] == "PED-000001"
    assert order["status"] == "pendiente"
    assert order["status_label"] == "Pendiente"
    assert order["subtotal"] == "6.00"
    assert order["total"] == "6.50"
    assert order["balance_due"] == "6.50"
    assert order["is_paid"] is False
    assert order["table_number"] == 1
    assert order["item_count"] == 1
    assert order["notes"] == "para llevar"
    assert order["allowed_transitions"] == ["cancelado", "preparando"]
    line = order["items"][0]
    assert line["product_name"] == "Espresso"
    assert line["unit_price"] == "2.00"
    assert line["subtotal"] == "6.00"

    product = await client.get(f"{API_PREFIX}/products/{espresso_id}", headers=headers)
    assert product.json()["stock"] == 7


async def test_order_with_two_lines_sums_the_subtotal(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Several lines are added together and the discount is applied."""
    response = await client.post(
        f"{API_PREFIX}/orders",
        json={
            "items": [
                {"product_id": catalog["espresso_id"], "quantity": 2},
                {"product_id": catalog["toast_id"], "quantity": 1},
            ],
            "discount": "1.00",
        },
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["subtotal"] == "7.50"
    assert body["discount"] == "1.00"
    assert body["total"] == "6.50"
    assert body["item_count"] == 2


async def test_repeated_product_lines_are_merged(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """The same product requested twice becomes a single line."""
    headers = auth_header(cashier_token)
    product_id = int(catalog["espresso_id"])

    response = await client.post(
        f"{API_PREFIX}/orders",
        json={
            "items": [
                {"product_id": product_id, "quantity": 1},
                {"product_id": product_id, "quantity": 2},
            ]
        },
        headers=headers,
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["item_count"] == 1
    assert body["items"][0]["quantity"] == 3
    assert body["total"] == "6.00"


async def test_order_without_items_returns_422(client: AsyncClient, cashier_token: str) -> None:
    """At least one line is required."""
    response = await client.post(
        f"{API_PREFIX}/orders",
        json={"items": []},
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_order_with_insufficient_stock_returns_422(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """The API refuses to sell more units than available."""
    headers = catalog["headers"]
    assert isinstance(headers, dict)
    scarce = await _product(
        client, headers, int(catalog["category_id"]), name="Té Rojo", price="2.00", stock=1
    )

    response = await client.post(
        f"{API_PREFIX}/orders",
        json={"items": [{"product_id": scarce["id"], "quantity": 5}]},
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "insufficient_stock"
    assert error["details"]["available"] == 1


async def test_order_with_unknown_product_returns_404(
    client: AsyncClient, cashier_token: str
) -> None:
    """Referencing a missing product is a 404."""
    response = await client.post(
        f"{API_PREFIX}/orders",
        json={"items": [{"product_id": 4242, "quantity": 1}]},
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_discount_greater_than_subtotal_is_rejected(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """A discount bigger than the subtotal is refused."""
    response = await client.post(
        f"{API_PREFIX}/orders",
        json={
            "items": [{"product_id": catalog["espresso_id"], "quantity": 1}],
            "discount": "10.00",
        },
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "business_rule_violation"


async def test_order_with_unknown_table_returns_404(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Referencing a missing table is a 404."""
    response = await client.post(
        f"{API_PREFIX}/orders",
        json={"items": [{"product_id": catalog["espresso_id"], "quantity": 1}], "table_id": 999},
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 404


async def test_table_cannot_have_two_open_orders(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object], table: dict[str, object]
) -> None:
    """A table with an open order rejects new orders."""
    headers = auth_header(cashier_token)
    espresso_id = int(catalog["espresso_id"])
    await _order(client, headers, espresso_id, table_id=table["id"])

    occupied = await client.get(
        f"{API_PREFIX}/tables", params={"is_occupied": True}, headers=headers
    )
    assert occupied.json()["total"] == 1
    assert occupied.json()["items"][0]["number"] == table["number"]

    response = await client.post(
        f"{API_PREFIX}/orders",
        json={"items": [{"product_id": espresso_id, "quantity": 1}], "table_id": table["id"]},
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "conflict"


async def test_full_status_flow_reaches_delivered(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Pending → preparando → listo → entregado."""
    headers = auth_header(cashier_token)
    espresso_id = int(catalog["espresso_id"])
    order = await _order(client, headers, espresso_id, quantity=2)

    for status, allowed in (
        ("preparando", ["cancelado", "listo"]),
        ("listo", ["entregado"]),
        ("entregado", []),
    ):
        response = await client.patch(
            f"{API_PREFIX}/orders/{order['id']}/status",
            json={"status": status},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == status
        assert response.json()["allowed_transitions"] == allowed

    delivered = await client.get(f"{API_PREFIX}/orders/{order['id']}", headers=headers)
    assert delivered.json()["delivered_at"] is not None

    product = await client.get(f"{API_PREFIX}/products/{espresso_id}", headers=headers)
    assert product.json()["stock"] == 8


async def test_invalid_transition_is_rejected(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """An order cannot jump from pending to delivered."""
    headers = auth_header(cashier_token)
    order = await _order(client, headers, int(catalog["espresso_id"]))

    response = await client.patch(
        f"{API_PREFIX}/orders/{order['id']}/status",
        json={"status": "entregado"},
        headers=headers,
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "business_rule_violation"
    assert error["details"]["current_status"] == "pendiente"


async def test_repeated_status_is_rejected(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Repeating the current status is refused."""
    headers = auth_header(cashier_token)
    order = await _order(client, headers, int(catalog["espresso_id"]))

    response = await client.patch(
        f"{API_PREFIX}/orders/{order['id']}/status",
        json={"status": "pendiente"},
        headers=headers,
    )

    assert response.status_code == 422


async def test_cancel_order_restores_stock(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object], table: dict[str, object]
) -> None:
    """Cancelling returns the reserved units to the catalogue."""
    headers = auth_header(cashier_token)
    espresso_id = int(catalog["espresso_id"])
    order = await _order(client, headers, espresso_id, quantity=3, table_id=table["id"])

    cancelled = await client.post(
        f"{API_PREFIX}/orders/{order['id']}/cancel",
        json={"reason": "el cliente se fue"},
        headers=headers,
    )

    assert cancelled.status_code == 200, cancelled.text
    assert cancelled.json()["status"] == "cancelado"
    assert cancelled.json()["cancelled_reason"] == "el cliente se fue"

    product = await client.get(f"{API_PREFIX}/products/{espresso_id}", headers=headers)
    assert product.json()["stock"] == 10

    tables = await client.get(f"{API_PREFIX}/tables", headers=headers)
    assert tables.json()["items"][0]["is_occupied"] is False


async def test_cancel_without_reason_is_rejected(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """The cancellation reason is mandatory."""
    headers = auth_header(cashier_token)
    order = await _order(client, headers, int(catalog["espresso_id"]))

    response = await client.post(
        f"{API_PREFIX}/orders/{order['id']}/cancel",
        json={"reason": "x"},
        headers=headers,
    )

    assert response.status_code == 422


async def test_delivered_order_cannot_be_cancelled(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Once delivered there are no transitions left."""
    headers = auth_header(cashier_token)
    order = await _order(client, headers, int(catalog["espresso_id"]))
    for status in ("preparando", "listo", "entregado"):
        await client.patch(
            f"{API_PREFIX}/orders/{order['id']}/status",
            json={"status": status},
            headers=headers,
        )

    response = await client.post(
        f"{API_PREFIX}/orders/{order['id']}/cancel",
        json={"reason": "tarde"},
        headers=headers,
    )

    assert response.status_code == 422


async def test_list_orders_with_filters_and_pagination(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Orders can be filtered by status and searched by code."""
    headers = auth_header(cashier_token)
    espresso_id = int(catalog["espresso_id"])
    first = await _order(client, headers, espresso_id, quantity=1)
    await _order(client, headers, espresso_id, quantity=1)
    await client.patch(
        f"{API_PREFIX}/orders/{first['id']}/status",
        json={"status": "preparando"},
        headers=headers,
    )

    pending = await client.get(
        f"{API_PREFIX}/orders", params={"status": "pendiente"}, headers=headers
    )
    assert pending.status_code == 200
    assert pending.json()["total"] == 1

    preparing = await client.get(
        f"{API_PREFIX}/orders", params={"status": "preparando"}, headers=headers
    )
    assert preparing.json()["total"] == 1

    by_code = await client.get(
        f"{API_PREFIX}/orders",
        params={"search": first["code"]},
        headers=headers,
    )
    assert by_code.json()["total"] == 1

    paginated = await client.get(
        f"{API_PREFIX}/orders",
        params={"size": 1, "sort_by": "created_at", "sort_dir": "asc"},
        headers=headers,
    )
    assert paginated.json()["total"] == 2
    assert paginated.json()["pages"] == 2
    assert paginated.json()["has_next"] is True


async def test_list_orders_filters_by_date(
    client: AsyncClient, cashier_token: str, catalog: dict[str, object]
) -> None:
    """A date range that does not contain the order returns nothing."""
    headers = auth_header(cashier_token)
    await _order(client, headers, int(catalog["espresso_id"]), quantity=1)

    response = await client.get(
        f"{API_PREFIX}/orders",
        params={"date_from": "2020-01-01", "date_to": "2020-01-02"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 0


async def test_kitchen_board_lists_preparing_and_ready_orders(
    client: AsyncClient, waiter_token: str, catalog: dict[str, object]
) -> None:
    """The board shows only the orders the kitchen is working on."""
    headers = auth_header(waiter_token)
    espresso_id = int(catalog["espresso_id"])
    pending = await _order(client, headers, espresso_id, quantity=1)
    preparing = await _order(client, headers, espresso_id, quantity=1)
    await client.patch(
        f"{API_PREFIX}/orders/{preparing['id']}/status",
        json={"status": "preparando"},
        headers=headers,
    )
    ready = await _order(client, headers, espresso_id, quantity=1)
    for status in ("preparando", "listo"):
        await client.patch(
            f"{API_PREFIX}/orders/{ready['id']}/status",
            json={"status": status},
            headers=headers,
        )

    board = await client.get(f"{API_PREFIX}/kitchen/board", headers=headers)

    assert board.status_code == 200
    codes = [item["code"] for item in board.json()]
    assert codes == [preparing["code"], ready["code"]]
    assert pending["code"] not in codes
    assert board.json()[0]["items"][0]["product_name"] == "Espresso"


async def test_waiter_can_create_orders(client: AsyncClient, waiter_token: str, catalog) -> None:
    """Waiters are allowed to create orders and move them forward."""
    headers = auth_header(waiter_token)

    created = await client.post(
        f"{API_PREFIX}/orders",
        json={"items": [{"product_id": catalog["espresso_id"], "quantity": 1}]},
        headers=headers,
    )
    assert created.status_code == 201

    advanced = await client.patch(
        f"{API_PREFIX}/orders/{created.json()['id']}/status",
        json={"status": "preparando"},
        headers=headers,
    )
    assert advanced.status_code == 200


async def test_waiter_cannot_cancel_orders(
    client: AsyncClient, waiter_token: str, cashier_token: str, catalog: dict[str, object]
) -> None:
    """Cancelling has financial impact so it needs admin or cashier."""
    headers = auth_header(cashier_token)
    order = await _order(client, headers, int(catalog["espresso_id"]), quantity=1)

    response = await client.post(
        f"{API_PREFIX}/orders/{order['id']}/cancel",
        json={"reason": "no lo quiero"},
        headers=auth_header(waiter_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_missing_order_returns_404(client: AsyncClient, waiter_token: str) -> None:
    """Unknown orders return the standard 404 envelope."""
    response = await client.get(f"{API_PREFIX}/orders/999", headers=auth_header(waiter_token))

    assert response.status_code == 404
