"""Tests for authentication, tokens and role based access control."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.security import create_access_token, decode_token, hash_password
from app.models import User
from app.tests.conftest import API_PREFIX, auth_header


async def test_login_returns_tokens(client: AsyncClient, admin_user: User) -> None:
    """Valid credentials return an access and a refresh token."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": admin_user.username, "password": "Test1234"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 1800
    payload = decode_token(body["access_token"], expected_type="access")
    assert int(payload["sub"]) == admin_user.id
    assert decode_token(body["refresh_token"], expected_type="refresh")


async def test_login_accepts_email_as_identifier(client: AsyncClient, admin_user: User) -> None:
    """The login also accepts the registered email address."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": admin_user.email, "password": "Test1234"},
    )

    assert response.status_code == 200


async def test_login_with_wrong_password_returns_401(client: AsyncClient, admin_user: User) -> None:
    """A wrong password produces a 401 with the standard envelope."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": admin_user.username, "password": "WrongPass1"},
    )

    assert response.status_code == 401
    error = response.json()["error"]
    assert error["code"] == "authentication_error"
    assert "incorrectos" in error["message"]


async def test_login_with_unknown_user_returns_401(client: AsyncClient) -> None:
    """Unknown identifiers return the same message as a wrong password."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": "nadie", "password": "Test1234"},
    )

    assert response.status_code == 401


async def test_login_with_inactive_user_returns_401(
    client: AsyncClient, inactive_user: User
) -> None:
    """Deactivated accounts cannot authenticate."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": inactive_user.username, "password": "Test1234"},
    )

    assert response.status_code == 401
    assert "desactivado" in response.json()["error"]["message"]


async def test_oauth2_form_login(client: AsyncClient, admin_user: User) -> None:
    """The OAuth2 password form flow used by /docs works."""
    response = await client.post(
        f"{API_PREFIX}/auth/login/form",
        data={"username": admin_user.username, "password": "Test1234"},
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


async def test_me_returns_the_profile(client: AsyncClient, admin_token: str) -> None:
    """The profile endpoint returns the authenticated user."""
    response = await client.get(f"{API_PREFIX}/auth/me", headers=auth_header(admin_token))

    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "admin"
    assert body["role"] == "admin"
    assert "hashed_password" not in body


async def test_me_without_token_returns_401(client: AsyncClient) -> None:
    """A missing token is rejected."""
    response = await client.get(f"{API_PREFIX}/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_error"


async def test_me_with_invalid_token_returns_401(client: AsyncClient) -> None:
    """A malformed token is rejected."""
    response = await client.get(
        f"{API_PREFIX}/auth/me",
        headers=auth_header("not-a-real-token"),
    )

    assert response.status_code == 401


async def test_refresh_token_issues_new_access_token(client: AsyncClient, admin_user: User) -> None:
    """A refresh token can be exchanged for a new access token."""
    login = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": admin_user.username, "password": "Test1234"},
    )
    refresh_token = login.json()["refresh_token"]

    response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": refresh_token},
    )

    assert response.status_code == 200
    assert response.json()["access_token"]


async def test_access_token_cannot_be_used_to_refresh(
    client: AsyncClient, admin_user: User
) -> None:
    """An access token is rejected by the refresh endpoint."""
    login = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": admin_user.username, "password": "Test1234"},
    )
    access_token = login.json()["access_token"]

    response = await client.post(
        f"{API_PREFIX}/auth/refresh",
        json={"refresh_token": access_token},
    )

    assert response.status_code == 401


async def test_change_password_and_login_with_new_one(
    client: AsyncClient,
    admin_user: User,
    session_factory: sessionmaker[Session],
) -> None:
    """The user can rotate the password and use the new one to log in."""
    token = (
        await client.post(
            f"{API_PREFIX}/auth/login",
            json={"username": admin_user.username, "password": "Test1234"},
        )
    ).json()["access_token"]

    response = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(token),
        json={"current_password": "Test1234", "new_password": "Nuevo12345"},
    )
    assert response.status_code == 200

    with session_factory() as session:
        stored = session.get(User, admin_user.id)
        assert stored is not None
        assert stored.hashed_password != hash_password("Test1234")

    relogin = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": admin_user.username, "password": "Nuevo12345"},
    )
    assert relogin.status_code == 200


async def test_change_password_rejects_wrong_current_password(
    client: AsyncClient, admin_token: str
) -> None:
    """The current password must match."""
    response = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(admin_token),
        json={"current_password": "Nope12345", "new_password": "Nuevo12345"},
    )

    assert response.status_code == 401


async def test_change_password_rejects_weak_password(client: AsyncClient, admin_token: str) -> None:
    """A password without letters and digits is rejected."""
    response = await client.post(
        f"{API_PREFIX}/auth/change-password",
        headers=auth_header(admin_token),
        json={"current_password": "Test1234", "new_password": "12345678"},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "business_rule_violation"


@pytest.mark.parametrize(
    ("username", "role", "method", "path", "payload", "expected"),
    [
        ("mesero", "mesero", "POST", "/categories", {"name": "Nueva"}, 403),
        ("cajero", "cajero", "POST", "/categories", {"name": "Nueva"}, 403),
        (
            "mesero",
            "mesero",
            "POST",
            "/products",
            {"name": "Nuevo", "price": "1.00", "category_id": 1},
            403,
        ),
    ],
)
async def test_roles_are_enforced(
    client: AsyncClient,
    session_factory: sessionmaker[Session],
    username: str,
    role: str,
    method: str,
    path: str,
    payload: dict[str, object],
    expected: int,
) -> None:
    """Categories are admin only and products require at least cashier."""
    from app.tests.conftest import _create_user

    user = _create_user(session_factory, username, role)
    token = (
        await client.post(
            f"{API_PREFIX}/auth/login",
            json={"username": username, "password": "Test1234"},
        )
    ).json()["access_token"]

    response = await client.request(
        method,
        f"{API_PREFIX}{path}",
        headers=auth_header(token),
        json=payload,
    )

    assert response.status_code == expected
    assert response.json()["error"]["code"] == "permission_denied"
    assert user.role.value == role


async def test_any_staff_role_can_list_products(client: AsyncClient, waiter_token: str) -> None:
    """Read operations are available to every staff role."""
    response = await client.get(
        f"{API_PREFIX}/products",
        headers=auth_header(waiter_token),
    )

    assert response.status_code == 200


async def test_protected_endpoint_requires_token(client: AsyncClient) -> None:
    """Listing products without a token is rejected."""
    response = await client.get(f"{API_PREFIX}/products")

    assert response.status_code == 401


async def test_token_of_deleted_user_is_rejected(
    client: AsyncClient, session_factory: sessionmaker[Session]
) -> None:
    """A token whose user no longer exists cannot be used."""
    from app.tests.conftest import _create_user

    user = _create_user(session_factory, "temporal", "mesero")
    token = create_access_token(user.id)

    with session_factory() as session:
        stored = session.get(User, user.id)
        assert stored is not None
        session.delete(stored)
        session.commit()

    response = await client.get(f"{API_PREFIX}/products", headers=auth_header(token))

    assert response.status_code == 401
