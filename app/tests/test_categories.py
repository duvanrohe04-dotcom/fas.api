from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Category


def test_listar_requiere_admin(client: TestClient, auth_header: dict[str, str]) -> None:
    """El listado de categorías requiere token."""
    assert client.get("/api/v1/categories").status_code == 401
    assert client.get("/api/v1/categories", headers=auth_header).status_code == 200


def test_crear_categoria(client: TestClient, auth_header: dict[str, str]) -> None:
    """Un admin puede crear una categoría."""
    response = client.post(
        "/api/v1/categories",
        headers=auth_header,
        json={"name": "Bebidas", "description": "Bebidas calientes y frías"},
    )

    assert response.status_code == 201
    assert response.json()["name"] == "Bebidas"
    assert response.json()["description"] == "Bebidas calientes y frías"


def test_crear_categoria_sin_permiso(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Un mesero no puede crear categorías."""
    token = client.post(
        "/api/v1/auth/login",
        json={
            "email": "mesero@test.com",
            "password": "meseropass123",
        },
    ).json()["access_token"]

    response = client.post(
        "/api/v1/categories",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "No permitido"},
    )

    assert response.status_code == 403


def test_nombre_duplicado(client: TestClient, auth_header: dict[str, str]) -> None:
    """No se pueden crear dos categorías con el mismo nombre."""
    payload = {"name": "Postres", "description": None}
    assert (
        client.post("/api/v1/categories", headers=auth_header, json=payload).status_code
        == 201
    )

    response = client.post("/api/v1/categories", headers=auth_header, json=payload)

    assert response.status_code == 400


def test_nombre_duplicado_ignora_mayusculas(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """La unicidad del nombre no distingue mayúsculas."""
    client.post("/api/v1/categories", headers=auth_header, json={"name": "Postres"})

    response = client.post(
        "/api/v1/categories", headers=auth_header, json={"name": "POSTRES"}
    )

    assert response.status_code == 400


def test_obtener_categoria(client: TestClient, auth_header: dict[str, str]) -> None:
    """Se puede consultar una categoría por su id."""
    created = client.post(
        "/api/v1/categories", headers=auth_header, json={"name": "Cafés"}
    ).json()

    response = client.get(f"/api/v1/categories/{created['id']}", headers=auth_header)

    assert response.status_code == 200
    assert response.json()["name"] == "Cafés"


def test_obtener_categoria_inexistente(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Un id inexistente devuelve 404."""
    response = client.get("/api/v1/categories/9999", headers=auth_header)

    assert response.status_code == 404


def test_actualizar_parcialmente(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Un PATCH solo modifica los campos enviados."""
    created = client.post(
        "/api/v1/categories",
        headers=auth_header,
        json={"name": "Bebidas", "description": "Frías"},
    ).json()

    response = client.patch(
        f"/api/v1/categories/{created['id']}",
        headers=auth_header,
        json={"name": "Bebidas frías"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "Bebidas frías"
    assert response.json()["description"] == "Frías"


def test_actualizar_con_nombre_duplicado(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """No se puede renombrar una categoría al nombre de otra."""
    client.post("/api/v1/categories", headers=auth_header, json={"name": "A"})
    segunda = client.post(
        "/api/v1/categories", headers=auth_header, json={"name": "B"}
    ).json()

    response = client.patch(
        f"/api/v1/categories/{segunda['id']}",
        headers=auth_header,
        json={"name": "A"},
    )

    assert response.status_code == 400


def test_eliminar_categoria(client: TestClient, auth_header: dict[str, str]) -> None:
    """Se puede eliminar una categoría vacía."""
    created = client.post(
        "/api/v1/categories", headers=auth_header, json={"name": "Temporal"}
    ).json()

    response = client.delete(f"/api/v1/categories/{created['id']}", headers=auth_header)

    assert response.status_code == 204
    assert (
        client.get(
            f"/api/v1/categories/{created['id']}", headers=auth_header
        ).status_code
        == 404
    )


def test_eliminar_categoria_con_productos(
    client: TestClient, auth_header: dict[str, str], session: Session
) -> None:
    """No se puede eliminar una categoría con productos activos."""
    from app.models import Product

    categoria = Category(name="Con productos")
    session.add(categoria)
    session.flush()
    session.add(
        Product(
            name="Café espresso",
            price=1.5,
            category_id=categoria.id,
            is_active=True,
        )
    )
    session.commit()

    response = client.delete(f"/api/v1/categories/{categoria.id}", headers=auth_header)

    assert response.status_code == 400


def test_eliminar_categoria_con_productos_inactivos(
    client: TestClient, auth_header: dict[str, str], session: Session
) -> None:
    """Sí se puede eliminar si sus productos están inactivos."""
    from app.models import Product

    categoria = Category(name="Solo inactivos")
    session.add(categoria)
    session.flush()
    session.add(
        Product(
            name="Producto retirado",
            price=1.0,
            category_id=categoria.id,
            is_active=False,
        )
    )
    session.commit()

    response = client.delete(f"/api/v1/categories/{categoria.id}", headers=auth_header)

    assert response.status_code == 204


def test_listar_paginado(client: TestClient, auth_header: dict[str, str]) -> None:
    """El listado respeta la paginación."""
    for name in ("A", "B", "C"):
        client.post("/api/v1/categories", headers=auth_header, json={"name": name})

    response = client.get("/api/v1/categories?page=1&size=2", headers=auth_header)

    body = response.json()
    assert response.status_code == 200
    assert body["total"] == 3
    assert body["pages"] == 2
    assert body["has_next"] is True
    assert body["has_prev"] is False
    assert [item["name"] for item in body["items"]] == ["A", "B"]


def test_paginacion_devuelve_estructura_completa(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Una página vacía tiene la forma correcta."""
    response = client.get("/api/v1/categories", headers=auth_header)

    body = response.json()
    assert body["items"] == []
    assert body["total"] == 0
    assert body["pages"] == 0
    assert body["has_next"] is False
    assert body["has_prev"] is False


def test_tamanio_de_pagina_invalido(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Un tamaño de página fuera de rango devuelve 422."""
    response = client.get("/api/v1/categories?size=500", headers=auth_header)

    assert response.status_code == 422
