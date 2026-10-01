import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category, Order, OrderStatus, Product


@pytest.fixture
def producto(session: Session) -> Product:
    categoria = Category(name="Bebidas")
    session.add(categoria)
    session.flush()
    nuevo = Product(name="Café espresso", price=1.5, stock=50, category_id=categoria.id)
    session.add(nuevo)
    session.commit()
    return nuevo


@pytest.fixture
def headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "adminpass123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _pedido(session: Session, status: OrderStatus) -> Order:
    order = Order(status=status, total_amount=0.0)
    session.add(order)
    session.commit()
    return order


def test_health(client: TestClient) -> None:
    """El health check responde sin autenticación."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_kitchen_requiere_token(client: TestClient) -> None:
    """La pantalla de cocina requiere autenticación."""
    assert client.get("/api/v1/kitchen/orders").status_code == 401


def test_kitchen_muestra_activos(
    client: TestClient, headers: dict[str, str], session: Session
) -> None:
    """Solo aparecen los pedidos pendientes y en preparación."""
    _pedido(session, OrderStatus.PENDING)
    _pedido(session, OrderStatus.PREPARING)
    _pedido(session, OrderStatus.READY)
    _pedido(session, OrderStatus.DELIVERED)
    _pedido(session, OrderStatus.CANCELLED)

    response = client.get("/api/v1/kitchen/orders", headers=headers)

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 2
    estados = {item["status"] for item in body["items"]}
    assert estados == {"pendiente", "preparando"}


def test_kitchen_vacia(client: TestClient, headers: dict[str, str]) -> None:
    """Sin pedidos activos devuelve una página vacía."""
    response = client.get("/api/v1/kitchen/orders", headers=headers)

    assert response.json()["total"] == 0
    assert response.json()["items"] == []
