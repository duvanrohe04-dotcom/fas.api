"""Tests for customers and tables."""

from __future__ import annotations

from httpx import AsyncClient

from app.tests.conftest import API_PREFIX, auth_header

CUSTOMER_PAYLOAD = {
    "name": "Lucía Fernández",
    "email": "lucia@example.com",
    "phone": "+34 600 123 456",
}


async def test_create_and_get_customer(client: AsyncClient, cashier_token: str) -> None:
    """A customer can be registered and read back."""
    headers = auth_header(cashier_token)
    created = await client.post(f"{API_PREFIX}/customers", json=CUSTOMER_PAYLOAD, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Lucía Fernández"
    assert body["is_active"] is True

    fetched = await client.get(f"{API_PREFIX}/customers/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["email"] == "lucia@example.com"


async def test_duplicate_customer_email_returns_409(
    client: AsyncClient, cashier_token: str
) -> None:
    """Two customers cannot share the same email."""
    headers = auth_header(cashier_token)
    await client.post(f"{API_PREFIX}/customers", json=CUSTOMER_PAYLOAD, headers=headers)

    duplicate = await client.post(
        f"{API_PREFIX}/customers",
        json={"name": "Otra persona", "email": "LUCIA@example.com"},
        headers=headers,
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


async def test_invalid_customer_email_returns_422(client: AsyncClient, cashier_token: str) -> None:
    """The email format is validated."""
    response = await client.post(
        f"{API_PREFIX}/customers",
        json={"name": "Lucía", "email": "no-es-un-email"},
        headers=auth_header(cashier_token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_update_and_delete_customer(client: AsyncClient, cashier_token: str) -> None:
    """PATCH updates a customer and DELETE removes it."""
    headers = auth_header(cashier_token)
    created = await client.post(f"{API_PREFIX}/customers", json=CUSTOMER_PAYLOAD, headers=headers)
    customer_id = created.json()["id"]

    patched = await client.patch(
        f"{API_PREFIX}/customers/{customer_id}",
        json={"name": "Lucía F. López"},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Lucía F. López"

    deleted = await client.delete(f"{API_PREFIX}/customers/{customer_id}", headers=headers)
    assert deleted.status_code == 200
    gone = await client.get(f"{API_PREFIX}/customers/{customer_id}", headers=headers)
    assert gone.status_code == 404


async def test_waiter_cannot_create_customers(client: AsyncClient, waiter_token: str) -> None:
    """Only admin and cashier manage customers."""
    response = await client.post(
        f"{API_PREFIX}/customers",
        json=CUSTOMER_PAYLOAD,
        headers=auth_header(waiter_token),
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "permission_denied"


async def test_create_and_list_tables(client: AsyncClient, cashier_token: str) -> None:
    """Tables can be registered and listed."""
    headers = auth_header(cashier_token)
    created = await client.post(
        f"{API_PREFIX}/tables",
        json={"number": 1, "name": "Ventana", "capacity": 4},
        headers=headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["is_occupied"] is False

    listed = await client.get(f"{API_PREFIX}/tables", headers=headers)
    assert listed.status_code == 200
    assert listed.json()["total"] == 1


async def test_duplicate_table_number_returns_409(client: AsyncClient, cashier_token: str) -> None:
    """Table numbers are unique."""
    headers = auth_header(cashier_token)
    payload = {"number": 7, "name": "Barra"}
    await client.post(f"{API_PREFIX}/tables", json=payload, headers=headers)

    duplicate = await client.post(
        f"{API_PREFIX}/tables",
        json={"number": 7, "name": "Otra"},
        headers=headers,
    )

    assert duplicate.status_code == 409


async def test_missing_table_returns_404(client: AsyncClient, waiter_token: str) -> None:
    """Unknown tables return the standard 404 envelope."""
    response = await client.get(f"{API_PREFIX}/tables/99", headers=auth_header(waiter_token))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"
