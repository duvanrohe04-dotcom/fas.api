"""Tests for the category endpoints."""

from __future__ import annotations

from httpx import AsyncClient

from app.tests.conftest import API_PREFIX, auth_header

CATEGORY_PAYLOAD = {
    "name": "Cafés",
    "description": "Espresso y filtrados.",
    "is_active": True,
}


async def test_create_and_get_category(client: AsyncClient, admin_token: str) -> None:
    """A category can be created and then read back."""
    headers = auth_header(admin_token)
    created = await client.post(f"{API_PREFIX}/categories", json=CATEGORY_PAYLOAD, headers=headers)
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["name"] == "Cafés"
    assert body["slug"] == "cafes"

    fetched = await client.get(f"{API_PREFIX}/categories/{body['id']}", headers=headers)
    assert fetched.status_code == 200
    assert fetched.json()["product_count"] == 0


async def test_duplicate_category_returns_409(client: AsyncClient, admin_token: str) -> None:
    """Creating a category with an existing name conflicts."""
    headers = auth_header(admin_token)
    await client.post(f"{API_PREFIX}/categories", json=CATEGORY_PAYLOAD, headers=headers)

    duplicate = await client.post(
        f"{API_PREFIX}/categories",
        json={**CATEGORY_PAYLOAD, "description": "Otra"},
        headers=headers,
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "conflict"


async def test_get_missing_category_returns_404(client: AsyncClient, admin_token: str) -> None:
    """Unknown identifiers produce a consistent 404 envelope."""
    response = await client.get(
        f"{API_PREFIX}/categories/999",
        headers=auth_header(admin_token),
    )

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert "999" in error["message"]


async def test_list_categories_paginated_and_sorted(client: AsyncClient, admin_token: str) -> None:
    """Listing supports pagination and sorting by name."""
    headers = auth_header(admin_token)
    for name in ("Postres", "Bebidas frías", "Panadería"):
        await client.post(f"{API_PREFIX}/categories", json={"name": name}, headers=headers)

    response = await client.get(
        f"{API_PREFIX}/categories",
        params={"sort_by": "name", "sort_dir": "asc", "size": 2, "page": 1},
        headers=headers,
    )

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 3
    assert page["pages"] == 2
    assert page["has_next"] is True
    assert page["has_prev"] is False
    assert [item["name"] for item in page["items"]] == ["Bebidas frías", "Panadería"]


async def test_search_filters_categories(client: AsyncClient, admin_token: str) -> None:
    """The search parameter filters by name, case insensitively."""
    headers = auth_header(admin_token)
    await client.post(f"{API_PREFIX}/categories", json={"name": "Cafés"}, headers=headers)
    await client.post(f"{API_PREFIX}/categories", json={"name": "Postres"}, headers=headers)

    response = await client.get(
        f"{API_PREFIX}/categories",
        params={"search": "caf"},
        headers=headers,
    )

    assert response.status_code == 200
    page = response.json()
    assert page["total"] == 1
    assert page["items"][0]["name"] == "Cafés"


async def test_update_and_activate_category(client: AsyncClient, admin_token: str) -> None:
    """PATCH updates fields and the activate endpoint re-enables a category."""
    headers = auth_header(admin_token)
    created = await client.post(
        f"{API_PREFIX}/categories",
        json=CATEGORY_PAYLOAD,
        headers=headers,
    )
    category_id = created.json()["id"]

    patched = await client.patch(
        f"{API_PREFIX}/categories/{category_id}",
        json={"description": "Actualizada", "is_active": False},
        headers=headers,
    )
    assert patched.status_code == 200
    assert patched.json()["description"] == "Actualizada"
    assert patched.json()["is_active"] is False

    activated = await client.post(
        f"{API_PREFIX}/categories/{category_id}/activate",
        headers=headers,
    )
    assert activated.status_code == 200
    assert activated.json()["is_active"] is True


async def test_delete_category_with_products_is_rejected(
    client: AsyncClient, admin_token: str
) -> None:
    """A category that still has products cannot be deleted."""
    headers = auth_header(admin_token)
    category = (
        await client.post(f"{API_PREFIX}/categories", json=CATEGORY_PAYLOAD, headers=headers)
    ).json()
    await client.post(
        f"{API_PREFIX}/products",
        json={
            "name": "Espresso",
            "description": "Carga simple",
            "price": "2.50",
            "category_id": category["id"],
            "stock": 20,
            "low_stock_threshold": 5,
        },
        headers=headers,
    )

    response = await client.delete(f"{API_PREFIX}/categories/{category['id']}", headers=headers)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "business_rule_violation"


async def test_delete_empty_category(client: AsyncClient, admin_token: str) -> None:
    """An empty category is removed successfully."""
    headers = auth_header(admin_token)
    category = (
        await client.post(f"{API_PREFIX}/categories", json=CATEGORY_PAYLOAD, headers=headers)
    ).json()

    response = await client.delete(f"{API_PREFIX}/categories/{category['id']}", headers=headers)

    assert response.status_code == 200
    assert response.json()["id"] == category["id"]
    gone = await client.get(f"{API_PREFIX}/categories/{category['id']}", headers=headers)
    assert gone.status_code == 404


async def test_category_validation_error_envelope(client: AsyncClient, admin_token: str) -> None:
    """Invalid payloads return the standard validation envelope."""
    response = await client.post(
        f"{API_PREFIX}/categories",
        json={"name": "x"},
        headers=auth_header(admin_token),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_category_by_slug_lookup(client: AsyncClient, admin_token: str) -> None:
    """A category can be fetched by its slug."""
    headers = auth_header(admin_token)
    await client.post(f"{API_PREFIX}/categories", json=CATEGORY_PAYLOAD, headers=headers)

    response = await client.get(f"{API_PREFIX}/categories/lookup/by-slug/cafes", headers=headers)

    assert response.status_code == 200
    assert response.json()["name"] == "Cafés"
