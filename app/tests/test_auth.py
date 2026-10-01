from fastapi.testclient import TestClient

from app.tests.conftest import (
    TEST_ADMIN_EMAIL,
    TEST_ADMIN_PASSWORD,
    TEST_WAITER_EMAIL,
    TEST_WAITER_PASSWORD,
)


def test_login_ok(client: TestClient) -> None:
    """Un usuario con credenciales válidas recibe token y datos."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == TEST_ADMIN_EMAIL
    assert body["user"]["role"] == "admin"


def test_login_no_expone_el_hash(client: TestClient) -> None:
    """La respuesta nunca incluye el hash de la contraseña."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )

    assert "hashed_password" not in response.json()["user"]
    assert TEST_ADMIN_PASSWORD not in response.text


def test_login_password_incorrecta(client: TestClient) -> None:
    """Una contraseña errónea devuelve 401."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": "incorrecta123"},
    )

    assert response.status_code == 401


def test_login_usuario_inexistente(client: TestClient) -> None:
    """Un email no registrado devuelve 401 sin filtrar información."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nadie@test.com", "password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 401


def test_login_email_normalizado(client: TestClient) -> None:
    """El email se busca sin distinguir mayúsculas."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL.upper(), "password": TEST_ADMIN_PASSWORD},
    )

    assert response.status_code == 200


def test_me_sin_token(client: TestClient) -> None:
    """`/auth/me` exige cabecera Authorization."""
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_me_con_token_valido(client: TestClient, auth_header: dict[str, str]) -> None:
    """`/auth/me` devuelve el usuario del token."""
    response = client.get("/api/v1/auth/me", headers=auth_header)

    assert response.status_code == 200
    assert response.json()["email"] == TEST_ADMIN_EMAIL


def test_me_con_token_invalido(client: TestClient) -> None:
    """Un token corrupto devuelve 401."""
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer no.es.un.token"}
    )

    assert response.status_code == 401


def test_crear_usuario_requiere_admin(
    client: TestClient, auth_header: dict[str, str]
) -> None:
    """Un admin puede crear usuarios."""
    response = client.post(
        "/api/v1/auth/users",
        headers=auth_header,
        json={
            "email": "nuevo@test.com",
            "password": "nuevopass123",
            "full_name": "Nuevo Usuario",
            "role": "cajero",
        },
    )

    assert response.status_code == 201
    assert response.json()["role"] == "cajero"


def test_crear_usuario_prohibido_para_no_admin(client: TestClient) -> None:
    """Un mesero no puede crear usuarios."""
    token = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_WAITER_EMAIL, "password": TEST_WAITER_PASSWORD},
    ).json()["access_token"]

    response = client.post(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "email": "intento@test.com",
            "password": "intento12345",
            "full_name": "Intento",
            "role": "admin",
        },
    )

    assert response.status_code == 403


def test_crear_usuario_requiere_autenticacion(client: TestClient) -> None:
    """Crear usuarios sin token devuelve 401."""
    response = client.post(
        "/api/v1/auth/users",
        json={
            "email": "sinauth@test.com",
            "password": "sinauth12345",
            "full_name": "Sin Auth",
            "role": "admin",
        },
    )

    assert response.status_code == 401


def test_email_duplicado(client: TestClient, auth_header: dict[str, str]) -> None:
    """No se pueden crear dos usuarios con el mismo email."""
    response = client.post(
        "/api/v1/auth/users",
        headers=auth_header,
        json={
            "email": TEST_ADMIN_EMAIL,
            "password": "otraclave123",
            "full_name": "Duplicado",
            "role": "cajero",
        },
    )

    assert response.status_code == 400
