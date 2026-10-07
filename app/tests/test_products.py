import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category


@pytest.fixture
def categoria(session: Session) -> Category:
    """Categoría de prueba reutilizable."""
    nueva = Category(name="Bebidas", description="Bebidas frías")
    session.add(nueva)
    session.commit()
    return nueva


def _crear_producto(client: TestClient, headers: dict[str, str], **overrides):
    payload = {
        "name": "Café espresso",
        "description": "Doble ristretto",
        "price": 1.5,
        "stock": 10,
        "category_id": 1,
    }
    payload.update(overrides)
    return client.post("/api/v1/products", headers=headers, json=payload)


def test_listar_es_publico(client: TestClient) -> None:
    """El listado de productos es público (menú del cliente)."""
    assert client.get("/api/v1/products").status_code == 200


def test_crear_producto(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Un admin puede crear un producto."""
    response = _crear_producto(client, auth_header, category_id=categoria.id)

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Café espresso"
    assert body["price"] == 1.5
    assert body["stock"] == 10
    assert body["is_active"] is True


def test_nombre_duplicado(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """No se pueden crear dos productos con el mismo nombre."""
    _crear_producto(client, auth_header, category_id=categoria.id)

    response = _crear_producto(
        client, auth_header, category_id=categoria.id, name="café espresso"
    )

    assert response.status_code == 400


def test_categoria_inexistente(client: TestClient, auth_header: dict[str, str]) -> None:
    """No se puede crear un producto en una categoría inexistente."""
    response = _crear_producto(client, auth_header, category_id=9999)

    assert response.status_code == 400


def test_precio_debe_ser_positivo(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El precio debe ser mayor que cero."""
    response = _crear_producto(client, auth_header, category_id=categoria.id, price=0)

    assert response.status_code == 422


def test_stock_negativo_en_creacion(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El stock no puede ser negativo al crear."""
    response = _crear_producto(client, auth_header, category_id=categoria.id, stock=-1)

    assert response.status_code == 422


def test_filtrar_por_categoria(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El listado se puede filtrar por categoría."""
    otra = client.post(
        "/api/v1/categories", headers=auth_header, json={"name": "Postres"}
    ).json()
    _crear_producto(client, auth_header, category_id=categoria.id)
    _crear_producto(client, auth_header, name="Tarta", category_id=otra["id"])

    response = client.get(
        f"/api/v1/products?category_id={categoria.id}", headers=auth_header
    )

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["name"] == "Café espresso"


def test_filtrar_por_estado(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El listado se puede filtrar por productos inactivos."""
    _crear_producto(client, auth_header, category_id=categoria.id)

    activos = client.get("/api/v1/products?is_active=true", headers=auth_header)
    inactivos = client.get("/api/v1/products?is_active=false", headers=auth_header)

    assert activos.json()["total"] == 1
    assert inactivos.json()["total"] == 0


def test_actualizar_producto(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Un PATCH modifica solo los campos enviados."""
    creado = _crear_producto(client, auth_header, category_id=categoria.id).json()

    response = client.patch(
        f"/api/v1/products/{creado['id']}",
        headers=auth_header,
        json={"price": 2.0},
    )

    assert response.status_code == 200
    assert response.json()["price"] == 2.0
    assert response.json()["name"] == "Café espresso"
    assert response.json()["stock"] == 10


def test_activar_y_desactivar(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Se puede desactivar un producto sin borrarlo."""
    creado = _crear_producto(client, auth_header, category_id=categoria.id).json()

    response = client.patch(
        f"/api/v1/products/{creado['id']}",
        headers=auth_header,
        json={"is_active": False},
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False


def test_ajustar_stock_absoluto(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El ajuste absoluto fija la cantidad de stock."""
    creado = _crear_producto(
        client, auth_header, category_id=categoria.id, stock=10
    ).json()

    response = client.patch(
        f"/api/v1/products/{creado['id']}/stock",
        headers=auth_header,
        json={"stock": 3},
    )

    assert response.status_code == 200
    assert response.json()["stock"] == 3


def test_ajustar_stock_por_delta(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El ajuste por delta suma al stock actual."""
    creado = _crear_producto(
        client, auth_header, category_id=categoria.id, stock=10
    ).json()

    restado = client.patch(
        f"/api/v1/products/{creado['id']}/stock",
        headers=auth_header,
        json={"delta": -4},
    )
    sumado = client.patch(
        f"/api/v1/products/{creado['id']}/stock",
        headers=auth_header,
        json={"delta": 2},
    )

    assert restado.json()["stock"] == 6
    assert sumado.json()["stock"] == 8


def test_ajustar_stock_no_negativo(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Un delta que dejaría el stock en negativo se rechaza."""
    creado = _crear_producto(
        client, auth_header, category_id=categoria.id, stock=2
    ).json()

    response = client.patch(
        f"/api/v1/products/{creado['id']}/stock",
        headers=auth_header,
        json={"delta": -5},
    )

    assert response.status_code == 400


def test_ajustar_stock_sin_campos(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """El ajuste exige `stock` o `delta`."""
    creado = _crear_producto(client, auth_header, category_id=categoria.id).json()

    response = client.patch(
        f"/api/v1/products/{creado['id']}/stock", headers=auth_header, json={}
    )

    assert response.status_code == 400


def test_cajero_puede_ajustar_stock(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Un cajero puede ajustar stock, aunque no crear productos."""
    creado = _crear_producto(client, auth_header, category_id=categoria.id).json()
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "adminpass123"},
    ).json()["access_token"]

    response = client.patch(
        f"/api/v1/products/{creado['id']}/stock",
        headers={"Authorization": f"Bearer {token}"},
        json={"delta": 5},
    )

    assert response.status_code == 200


def test_eliminar_producto(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Un admin puede eliminar un producto."""
    creado = _crear_producto(client, auth_header, category_id=categoria.id).json()

    response = client.delete(f"/api/v1/products/{creado['id']}", headers=auth_header)

    assert response.status_code == 204
    assert (
        client.get(f"/api/v1/products/{creado['id']}", headers=auth_header).status_code
        == 404
    )


def test_mesero_no_puede_crear(
    client: TestClient, auth_header: dict[str, str], categoria: Category
) -> None:
    """Un mesero no puede crear productos."""
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "mesero@test.com", "password": "meseropass123"},
    ).json()["access_token"]

    response = _crear_producto(
        client,
        {"Authorization": f"Bearer {token}"},
        category_id=categoria.id,
    )

    assert response.status_code == 403
