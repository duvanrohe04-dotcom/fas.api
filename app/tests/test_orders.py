import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category, Product, Table, TableStatus

CATEGORIA = "Bebidas"
PRODUCTO = "Café espresso"
PRECIO = 1.5


@pytest.fixture
def categoria(session: Session) -> Category:
    nueva = Category(name=CATEGORIA)
    session.add(nueva)
    session.commit()
    return nueva


@pytest.fixture
def producto(session: Session, categoria: Category) -> Product:
    nuevo = Product(
        name=PRODUCTO, price=PRECIO, stock=20, category_id=categoria.id, is_active=True
    )
    session.add(nuevo)
    session.commit()
    return nuevo


@pytest.fixture
def mesa(session: Session) -> Table:
    nueva = Table(number=1, capacity=4)
    session.add(nueva)
    session.commit()
    return nueva


@pytest.fixture
def waiter_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "mesero@test.com", "password": "meseropass123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _crear_pedido(client: TestClient, headers: dict[str, str], **overrides):
    items = overrides.pop("items", None)
    if items is None:
        items = [
            {
                "product_id": overrides.pop("product_id", 1),
                "quantity": overrides.pop("quantity", 1),
            }
        ]
    payload = {"items": items}
    payload.update(overrides)
    return client.post("/api/v1/orders", headers=headers, json=payload)


def test_crear_pedido_calcula_total(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """El total se calcula como precio unitario por cantidad."""
    response = _crear_pedido(client, waiter_headers, product_id=producto.id, quantity=3)

    assert response.status_code == 201
    body = response.json()
    assert body["total_amount"] == pytest.approx(4.5)
    assert len(body["items"]) == 1
    assert body["items"][0]["subtotal"] == pytest.approx(4.5)
    assert body["status"] == "pendiente"


def test_crear_pedido_descuenta_stock(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Crear un pedido descuenta el stock del producto."""
    _crear_pedido(client, waiter_headers, product_id=producto.id, quantity=3)

    session.refresh(producto)
    assert producto.stock == 17


def test_crear_pedido_ocupa_mesa(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    mesa: Table,
    session: Session,
) -> None:
    """Crear un pedido marca la mesa como ocupada."""
    _crear_pedido(client, waiter_headers, product_id=producto.id, table_id=mesa.id)

    session.refresh(mesa)
    assert mesa.status == TableStatus.OCCUPIED


def test_crear_pedido_sin_mesas(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """Un pedido puede no estar asociado a ninguna mesa."""
    response = _crear_pedido(client, waiter_headers, product_id=producto.id)

    assert response.status_code == 201
    assert response.json()["table_id"] is None


def test_pedido_sin_productos(
    client: TestClient, waiter_headers: dict[str, str]
) -> None:
    """Un pedido debe tener al menos una línea."""
    response = client.post("/api/v1/orders", headers=waiter_headers, json={"items": []})

    assert response.status_code == 422


def test_producto_inexistente(
    client: TestClient, waiter_headers: dict[str, str]
) -> None:
    """No se puede pedir un producto inexistente."""
    response = client.post(
        "/api/v1/orders",
        headers=waiter_headers,
        json={"items": [{"product_id": 9999, "quantity": 1}]},
    )

    assert response.status_code == 400


def test_stock_insuficiente(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """No se puede pedir más stock del disponible."""
    producto.stock = 1
    session.commit()

    response = _crear_pedido(client, waiter_headers, product_id=producto.id, quantity=5)

    assert response.status_code == 400


def test_producto_inactivo_no_se_pide(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """No se puede pedir un producto desactivado."""
    producto.is_active = False
    session.commit()

    response = _crear_pedido(client, waiter_headers, product_id=producto.id)

    assert response.status_code == 400


def test_mesas_inexistente(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """No se puede asignar una mesa inexistente."""
    response = _crear_pedido(
        client, waiter_headers, product_id=producto.id, table_id=9999
    )

    assert response.status_code == 400


def test_anadir_productos_actualiza_total(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """Añadir líneas recalcula el total."""
    pedido = _crear_pedido(
        client, waiter_headers, product_id=producto.id, quantity=2
    ).json()

    response = client.post(
        f"/api/v1/orders/{pedido['id']}/items",
        headers=waiter_headers,
        json={"items": [{"product_id": producto.id, "quantity": 1}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total_amount"] == pytest.approx(4.5)
    assert body["items"][0]["quantity"] == 3


def test_quitar_producto_devuelve_stock(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Quitar una línea devuelve el stock y recalcula el total."""
    pedido = _crear_pedido(
        client, waiter_headers, product_id=producto.id, quantity=2
    ).json()
    item_id = pedido["items"][0]["id"]

    response = client.delete(
        f"/api/v1/orders/{pedido['id']}/items/{item_id}", headers=waiter_headers
    )

    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["total_amount"] == pytest.approx(0.0)
    session.refresh(producto)
    assert producto.stock == 20


def test_transicion_de_estados(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """Un pedido recorre pendiente → preparando → listo → entregado."""
    pedido = _crear_pedido(client, waiter_headers, product_id=producto.id).json()

    for esperado in ("preparando", "listo", "entregado"):
        response = client.patch(
            f"/api/v1/orders/{pedido['id']}/status",
            headers=waiter_headers,
            json={"status": esperado},
        )
        assert response.status_code == 200
        assert response.json()["status"] == esperado


def test_transicion_invalida(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """No se puede saltar de pendiente a entregado."""
    pedido = _crear_pedido(client, waiter_headers, product_id=producto.id).json()

    response = client.patch(
        f"/api/v1/orders/{pedido['id']}/status",
        headers=waiter_headers,
        json={"status": "entregado"},
    )

    assert response.status_code == 400


def test_cancelar_devuelve_stock(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Cancelar un pedido devuelve el stock de sus líneas."""
    pedido = _crear_pedido(
        client, waiter_headers, product_id=producto.id, quantity=4
    ).json()

    response = client.patch(
        f"/api/v1/orders/{pedido['id']}/status",
        headers=waiter_headers,
        json={"status": "cancelado"},
    )

    assert response.status_code == 200
    session.refresh(producto)
    assert producto.stock == 20


def test_cancelar_libera_mesa(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    mesa: Table,
    session: Session,
) -> None:
    """Cancelar el único pedido activo libera la mesa."""
    pedido = _crear_pedido(
        client, waiter_headers, product_id=producto.id, table_id=mesa.id
    ).json()

    client.patch(
        f"/api/v1/orders/{pedido['id']}/status",
        headers=waiter_headers,
        json={"status": "cancelado"},
    )

    session.refresh(mesa)
    assert mesa.status == TableStatus.AVAILABLE


def test_entregar_libera_mesa(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    mesa: Table,
    session: Session,
) -> None:
    """Entregar el pedido libera la mesa."""
    pedido = _crear_pedido(
        client, waiter_headers, product_id=producto.id, table_id=mesa.id
    ).json()

    for estado in ("preparando", "listo", "entregado"):
        client.patch(
            f"/api/v1/orders/{pedido['id']}/status",
            headers=waiter_headers,
            json={"status": estado},
        )

    session.refresh(mesa)
    assert mesa.status == TableStatus.AVAILABLE


def test_mesa_no_se_libera_con_otro_pedido_activo(
    client: TestClient,
    waiter_headers: dict[str, str],
    producto: Product,
    mesa: Table,
    session: Session,
) -> None:
    """La mesa sigue ocupada si tiene otro pedido en curso."""
    pedido = _crear_pedido(
        client, waiter_headers, product_id=producto.id, table_id=mesa.id
    ).json()
    _crear_pedido(client, waiter_headers, product_id=producto.id, table_id=mesa.id)

    client.patch(
        f"/api/v1/orders/{pedido['id']}/status",
        headers=waiter_headers,
        json={"status": "cancelado"},
    )

    session.refresh(mesa)
    assert mesa.status == TableStatus.OCCUPIED


def test_anadir_items_a_pedido_entregado(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """No se añaden líneas a un pedido ya entregado."""
    pedido = _crear_pedido(client, waiter_headers, product_id=producto.id).json()
    for estado in ("preparando", "listo", "entregado"):
        client.patch(
            f"/api/v1/orders/{pedido['id']}/status",
            headers=waiter_headers,
            json={"status": estado},
        )

    response = client.post(
        f"/api/v1/orders/{pedido['id']}/items",
        headers=waiter_headers,
        json={"items": [{"product_id": producto.id, "quantity": 1}]},
    )

    assert response.status_code == 400


def test_filtrar_pedidos_por_estado(
    client: TestClient, waiter_headers: dict[str, str], producto: Product
) -> None:
    """El listado se puede filtrar por estado."""
    pedido = _crear_pedido(client, waiter_headers, product_id=producto.id).json()
    client.patch(
        f"/api/v1/orders/{pedido['id']}/status",
        headers=waiter_headers,
        json={"status": "preparando"},
    )

    preparando = client.get("/api/v1/orders?status=preparando", headers=waiter_headers)
    pendientes = client.get("/api/v1/orders?status=pendiente", headers=waiter_headers)

    assert preparando.json()["total"] == 1
    assert pendientes.json()["total"] == 0


def test_pedido_inexistente(client: TestClient, waiter_headers: dict[str, str]) -> None:
    """Un id de pedido inexistente devuelve 404."""
    response = client.get("/api/v1/orders/9999", headers=waiter_headers)

    assert response.status_code == 404
