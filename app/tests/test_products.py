"""Tests for the product endpoints."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.models import Product
from app.tests.conftest import API_PREFIX, auth_header


async def _create_category(
    client: AsyncClient,
    headers: dict[str, str],
    name: str = "Cafés",
) -> dict[str, object]:
    """Create a category and return its JSON payload."""
    response = await client.post(f"{API_PREFIX}/categories", json={"name": name}, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


async def _create_product(
    client: AsyncClient,
    headers: dict[str, str],
    category_id: int,
    **overrides: object,
) -> dict[str, object]:
    """Create a product inside the given category."""
    payload: dict[str, object] = {
        "name": "Espresso doble",
        "description": "Doble carga de espresso.",
        "price": "2.80",
        "category_id": category_id,
        "stock": 40,
        "low_stock_threshold": 10,
    }
    payload.update(overrides)
    response = await client.post(f"{API_PREFIX}/products", json=payload, headers=headers)
    assert response.status_code == 201, response.text
    return response.json()  # type: ignore[no-any-return]


async def test_create_product_with_computed_flags(client: AsyncClient, admin_token: str) -> None:
    """A created product exposes category name and stock flags."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)

    product = await _create_product(client, headers, int(category["id"]))

    assert product["price"] == "2.80"
    assert product["category_name"] == "Cafés"
    assert product["is_low_stock"] is False
    assert product["is_available"] is True


async def test_create_product_with_missing_category_returns_404(
    client: AsyncClient, admin_token: str
) -> None:
    """A product cannot reference a non existing category."""
    response = await client.post(
        f"{API_PREFIX}/products",
        json={"name": "Fantasía", "price": "1.00", "category_id": 999, "stock": 1},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_price_rejects_more_than_two_decimals(client: AsyncClient, admin_token: str) -> None:
    """Prices with three decimals are rejected by validation."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)

    response = await client.post(
        f"{API_PREFIX}/products",
        json={"name": "Redondo", "price": "3.456", "category_id": category["id"]},
        headers=headers,
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_price_is_always_rendered_with_two_decimals(
    client: AsyncClient, admin_token: str
) -> None:
    """The API always renders prices with exactly two decimals."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)

    product = await _create_product(client, headers, int(category["id"]), price="4.50")

    assert product["price"] == "4.50"

    refetched = await client.get(f"{API_PREFIX}/products/{product['id']}", headers=headers)
    assert refetched.json()["price"] == "4.50"


async def test_list_products_with_filters_and_pagination(
    client: AsyncClient, admin_token: str
) -> None:
    """Products can be filtered by category and low stock flag."""
    headers = auth_header(admin_token)
    cafes = await _create_category(client, headers, "Cafés")
    postres = await _create_category(client, headers, "Postres")
    await _create_product(
        client, headers, int(cafes["id"]), name="Espresso", stock=50, low_stock_threshold=5
    )
    await _create_product(
        client, headers, int(cafes["id"]), name="Cortado", stock=2, low_stock_threshold=5
    )
    await _create_product(
        client, headers, int(postres["id"]), name="Tarta", stock=8, low_stock_threshold=5
    )

    by_category = await client.get(
        f"{API_PREFIX}/products",
        params={"category_id": cafes["id"]},
        headers=headers,
    )
    assert by_category.status_code == 200
    assert by_category.json()["total"] == 2

    low_stock = await client.get(
        f"{API_PREFIX}/products",
        params={"low_stock": True},
        headers=headers,
    )
    assert low_stock.json()["total"] == 1
    assert low_stock.json()["items"][0]["name"] == "Cortado"

    not_low_stock = await client.get(
        f"{API_PREFIX}/products",
        params={"low_stock": False},
        headers=headers,
    )
    assert not_low_stock.json()["total"] == 2

    inactive = await client.get(
        f"{API_PREFIX}/products",
        params={"is_active": False},
        headers=headers,
    )
    assert inactive.json()["total"] == 0


async def test_list_products_sorted_by_price(client: AsyncClient, admin_token: str) -> None:
    """Sorting by price ascending returns the cheapest product first."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)
    await _create_product(client, headers, int(category["id"]), name="Caro", price="9.90")
    await _create_product(client, headers, int(category["id"]), name="Barato", price="1.10")

    response = await client.get(
        f"{API_PREFIX}/products",
        params={"sort_by": "price", "sort_dir": "asc"},
        headers=headers,
    )

    assert response.status_code == 200
    assert [item["name"] for item in response.json()["items"]] == ["Barato", "Caro"]


async def test_update_product(client: AsyncClient, admin_token: str) -> None:
    """PATCH updates price and stock partially."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)
    product = await _create_product(client, headers, int(category["id"]))

    response = await client.patch(
        f"{API_PREFIX}/products/{product['id']}",
        json={"price": "3.10", "stock": 12},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["price"] == "3.10"
    assert response.json()["stock"] == 12
    assert response.json()["name"] == "Espresso doble"


async def test_increase_stock_endpoint(client: AsyncClient, admin_token: str) -> None:
    """The stock endpoint adds units to the current stock."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)
    product = await _create_product(
        client, headers, int(category["id"]), stock=10, low_stock_threshold=5
    )

    response = await client.post(
        f"{API_PREFIX}/products/{product['id']}/stock",
        json={"quantity": 15, "reason": "recepción"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["stock"] == 25


async def test_increase_stock_rejects_non_positive_quantity(
    client: AsyncClient, admin_token: str
) -> None:
    """Only positive quantities are accepted."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)
    product = await _create_product(client, headers, int(category["id"]))

    response = await client.post(
        f"{API_PREFIX}/products/{product['id']}/stock",
        json={"quantity": 0},
        headers=headers,
    )

    assert response.status_code == 422


async def test_delete_product(client: AsyncClient, admin_token: str) -> None:
    """A product without orders can be deleted."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)
    product = await _create_product(client, headers, int(category["id"]))

    response = await client.delete(f"{API_PREFIX}/products/{product['id']}", headers=headers)

    assert response.status_code == 200
    gone = await client.get(f"{API_PREFIX}/products/{product['id']}", headers=headers)
    assert gone.status_code == 404


async def test_list_products_of_category(client: AsyncClient, admin_token: str) -> None:
    """The nested category route lists only its own products."""
    headers = auth_header(admin_token)
    cafes = await _create_category(client, headers, "Cafés")
    postres = await _create_category(client, headers, "Postres")
    await _create_product(client, headers, int(cafes["id"]), name="Espresso")
    await _create_product(client, headers, int(postres["id"]), name="Tarta")

    response = await client.get(
        f"{API_PREFIX}/categories/{cafes['id']}/products",
        headers=headers,
    )

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert page["items"][0]["name"] == "Espresso"


async def test_get_product_by_missing_id_returns_404(client: AsyncClient, admin_token: str) -> None:
    """Unknown products return the 404 envelope."""
    response = await client.get(
        f"{API_PREFIX}/products/12345",
        headers=auth_header(admin_token),
    )

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


async def test_writes_are_committed_to_the_database(
    client: AsyncClient,
    session_factory: sessionmaker[Session],
    admin_token: str,
) -> None:
    """A product created through the API is visible from a brand new session."""
    headers = auth_header(admin_token)
    category = await _create_category(client, headers)
    product = await _create_product(client, headers, int(category["id"]))

    with session_factory() as session:
        stored = session.get(Product, product["id"])

    assert stored is not None
    assert stored.name == "Espresso doble"
    assert stored.stock == 40
