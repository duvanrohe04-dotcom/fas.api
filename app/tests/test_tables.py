import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, Table, TableStatus


@pytest.fixture
def mesa(session: Session) -> Table:
    """Mesa de prueba reutilizable."""
    nueva = Table(number=1, capacity=4)
    session.add(nueva)
    session.commit()
    return nueva


def test_listar_requiere_token(client: TestClient) -> None:
    """El listado de mesas requiere autenticación."""
    assert client.get("/api/v1/tables").status_code == 401


def test_crear_mesa(client: TestClient, auth_header: dict[str, str]) -> None:
    """Un admin puede crear una mesa disponible por defecto."""
    response = client.post(
        "/api/v1/tables", headers=auth_header, json={"number": 5, "capacity": 6}
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "number": 5,
        "capacity": 6,
        "status": "disponible",
    }


def test_numero_duplicado(
    client: TestClient, auth_header: dict[str, str], mesa: Table
) -> None:
    """No se pueden crear dos mesas con el mismo número."""
    response = client.post(
        "/api/v1/tables", headers=auth_header, json={"number": mesa.number}
    )

    assert response.status_code == 400


def test_capacidad_invalida(client: TestClient, auth_header: dict[str, str]) -> None:
    """La capacidad debe ser al menos 1."""
    response = client.post(
        "/api/v1/tables", headers=auth_header, json={"number": 7, "capacity": 0}
    )

    assert response.status_code == 422


def test_ocupar_mesa(
    client: TestClient, auth_header: dict[str, str], mesa: Table
) -> None:
    """Se puede marcar una mesa como ocupada."""
    response = client.patch(
        f"/api/v1/tables/{mesa.id}/status?status=ocupada", headers=auth_header
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ocupada"


def test_no_liberar_mesa_con_pedidos(
    client: TestClient, auth_header: dict[str, str], mesa: Table, session: Session
) -> None:
    """No se puede liberar una mesa con pedidos en curso."""
    session.add(Order(table_id=mesa.id, status=OrderStatus.PREPARING, total_amount=5.0))
    session.commit()
    mesa.status = TableStatus.OCCUPIED
    session.commit()

    response = client.patch(
        f"/api/v1/tables/{mesa.id}/status?status=disponible", headers=auth_header
    )

    assert response.status_code == 400


def test_liberar_mesa_sin_pedidos(
    client: TestClient, auth_header: dict[str, str], mesa: Table, session: Session
) -> None:
    """Una mesa cuyos pedidos están entregados se puede liberar."""
    session.add(Order(table_id=mesa.id, status=OrderStatus.DELIVERED))
    session.commit()
    mesa.status = TableStatus.OCCUPIED
    session.commit()

    response = client.patch(
        f"/api/v1/tables/{mesa.id}/status?status=disponible", headers=auth_header
    )

    assert response.status_code == 200
    assert response.json()["status"] == "disponible"


def test_filtrar_por_estado(client: TestClient, auth_header: dict[str, str]) -> None:
    """El listado se puede filtrar por estado."""
    client.post("/api/v1/tables", headers=auth_header, json={"number": 1})
    ocupada = client.post(
        "/api/v1/tables", headers=auth_header, json={"number": 2}
    ).json()
    client.patch(
        f"/api/v1/tables/{ocupada['id']}/status?status=ocupada", headers=auth_header
    )

    disponibles = client.get("/api/v1/tables?status=disponible", headers=auth_header)
    ocupadas = client.get("/api/v1/tables?status=ocupada", headers=auth_header)

    assert disponibles.json()["total"] == 1
    assert ocupadas.json()["total"] == 1


def test_filtrar_por_capacidad(client: TestClient, auth_header: dict[str, str]) -> None:
    """El listado se puede filtrar por capacidad mínima."""
    client.post(
        "/api/v1/tables", headers=auth_header, json={"number": 1, "capacity": 2}
    )
    client.post(
        "/api/v1/tables", headers=auth_header, json={"number": 2, "capacity": 8}
    )

    response = client.get("/api/v1/tables?min_capacity=4", headers=auth_header)

    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["capacity"] == 8


def test_actualizar_capacidad(
    client: TestClient, auth_header: dict[str, str], mesa: Table
) -> None:
    """Un PATCH modifica la capacidad."""
    response = client.patch(
        f"/api/v1/tables/{mesa.id}", headers=auth_header, json={"capacity": 10}
    )

    assert response.status_code == 200
    assert response.json()["capacity"] == 10


def test_eliminar_mesa(
    client: TestClient, auth_header: dict[str, str], mesa: Table
) -> None:
    """Un admin puede eliminar una mesa sin pedidos."""
    response = client.delete(f"/api/v1/tables/{mesa.id}", headers=auth_header)

    assert response.status_code == 204
    assert (
        client.get(f"/api/v1/tables/{mesa.id}", headers=auth_header).status_code == 404
    )


def test_no_eliminar_mesa_con_pedidos(
    client: TestClient, auth_header: dict[str, str], mesa: Table, session: Session
) -> None:
    """No se puede eliminar una mesa con pedidos en curso."""
    session.add(Order(table_id=mesa.id, status=OrderStatus.PENDING))
    session.commit()

    response = client.delete(f"/api/v1/tables/{mesa.id}", headers=auth_header)

    assert response.status_code == 400


def test_mesero_no_puede_crear(client: TestClient) -> None:
    """Un mesero no puede crear mesas."""
    token = client.post(
        "/api/v1/auth/login",
        json={"email": "mesero@test.com", "password": "meseropass123"},
    ).json()["access_token"]

    response = client.post(
        "/api/v1/tables",
        headers={"Authorization": f"Bearer {token}"},
        json={"number": 9},
    )

    assert response.status_code == 403
