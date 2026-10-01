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
def admin_headers(client: TestClient) -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@test.com", "password": "adminpass123"},
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _pedido(session: Session, producto: Product, cantidad: int = 2) -> Order:
    """Crea un pedido ya entregado directamente en base de datos."""
    from app.models import OrderItem

    order = Order(status=OrderStatus.DELIVERED, total_amount=1.5 * cantidad)
    session.add(order)
    session.flush()
    session.add(
        OrderItem(
            order_id=order.id,
            product_id=producto.id,
            quantity=cantidad,
            unit_price=1.5,
            subtotal=1.5 * cantidad,
        )
    )
    session.commit()
    return order


def test_cobrar_pedido(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Se cobra un pedido entregado con el importe exacto."""
    pedido = _pedido(session, producto)

    response = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 3.0},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == pytest.approx(3.0)
    assert body["method"] == "efectivo"
    assert body["order_id"] == pedido.id


def test_no_cobrar_dos_veces(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Un pedido no admite un segundo pago."""
    pedido = _pedido(session, producto)
    client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 3.0},
    )

    response = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "tarjeta", "amount": 3.0},
    )

    assert response.status_code == 400


def test_no_cobrar_importe_distinto(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """El importe debe coincidir con el total del pedido."""
    pedido = _pedido(session, producto)

    response = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 10.0},
    )

    assert response.status_code == 400


def test_no_cobrar_pedido_no_entregado(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """No se cobra un pedido que no está entregado."""
    order = Order(status=OrderStatus.PENDING, total_amount=3.0)
    session.add(order)
    session.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 3.0},
    )

    assert response.status_code == 400


def test_no_cobrar_pedido_vacio(
    client: TestClient, admin_headers: dict[str, str], session: Session
) -> None:
    """No se cobra un pedido sin líneas."""
    order = Order(status=OrderStatus.DELIVERED, total_amount=0.0)
    session.add(order)
    session.commit()

    response = client.post(
        f"/api/v1/orders/{order.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 0.0},
    )

    assert response.status_code in (400, 422)


def test_cobrar_pedido_inexistente(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    """Cobrar un pedido inexistente devuelve 404."""
    response = client.post(
        "/api/v1/orders/9999/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 3.0},
    )

    assert response.status_code == 404


def test_ver_pago(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Se puede consultar el pago de un pedido."""
    pedido = _pedido(session, producto)
    client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "tarjeta", "amount": 3.0},
    )

    response = client.get(f"/api/v1/orders/{pedido.id}/payment", headers=admin_headers)

    assert response.status_code == 200
    assert response.json()["method"] == "tarjeta"


def test_ver_pago_inexistente(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Un pedido sin pagar devuelve 404 al consultar su pago."""
    pedido = _pedido(session, producto)

    response = client.get(f"/api/v1/orders/{pedido.id}/payment", headers=admin_headers)

    assert response.status_code == 404


def test_anular_pago(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """Se anula un pago y luego se puede volver a cobrar."""
    pedido = _pedido(session, producto)
    client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 3.0},
    )

    anulado = client.delete(
        f"/api/v1/orders/{pedido.id}/payment", headers=admin_headers
    )
    assert anulado.status_code == 204

    recobro = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": 3.0},
    )
    assert recobro.status_code == 201


def test_cobrar_requiere_autenticacion(
    client: TestClient, producto: Product, session: Session
) -> None:
    """Cobrar un pedido requiere token."""
    pedido = _pedido(session, producto)

    response = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        json={"method": "efectivo", "amount": 3.0},
    )

    assert response.status_code == 401


def test_metodo_invalido(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """El método de pago debe ser uno de los válidos."""
    pedido = _pedido(session, producto)

    response = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "bitcoin", "amount": 3.0},
    )

    assert response.status_code == 422


def test_importe_debe_ser_positivo(
    client: TestClient,
    admin_headers: dict[str, str],
    producto: Product,
    session: Session,
) -> None:
    """El importe debe ser positivo."""
    pedido = _pedido(session, producto)

    response = client.post(
        f"/api/v1/orders/{pedido.id}/pay",
        headers=admin_headers,
        json={"method": "efectivo", "amount": -1},
    )

    assert response.status_code == 422
