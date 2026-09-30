"""Pytest configuration and shared fixtures."""

from __future__ import annotations

import os
from collections.abc import AsyncGenerator, Generator
from pathlib import Path

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

TEST_DB_FILE = Path(__file__).parent / "test_cafeteria.db"
API_PREFIX = "/api/v1"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_FILE.as_posix()}"
os.environ["ENVIRONMENT"] = "testing"
os.environ["SECRET_KEY"] = "test-secret-key-used-only-by-the-pytest-suite-0000"

from app.core.database import (  # noqa: E402
    database_health_dependency,
    get_db,
    register_sqlite_pragma,
)
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import User, UserRole  # noqa: E402


@pytest.fixture(scope="session")
def test_engine() -> Generator[Engine, None, None]:
    """Create an isolated SQLite engine for the whole test session."""
    engine = create_engine(
        f"sqlite:///{TEST_DB_FILE.as_posix()}",
        connect_args={"check_same_thread": False},
    )
    register_sqlite_pragma(engine)
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()
    if TEST_DB_FILE.exists():
        TEST_DB_FILE.unlink()


@pytest.fixture
def db(test_engine: Engine) -> Generator[Session, None, None]:
    """Provide a clean database for each test."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    session = Session(test_engine, expire_on_commit=False)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture
def session_factory(test_engine: Engine) -> sessionmaker[Session]:
    """Expose a session factory bound to the test engine."""
    return sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )


@pytest.fixture
def app(test_engine: Engine) -> FastAPI:
    """Build the application wired to the test database."""
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)
    application = create_app()
    factory = sessionmaker(
        bind=test_engine,
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
    )

    def _override_get_db() -> Generator[Session, None, None]:
        session = factory()
        try:
            yield session
        finally:
            session.close()

    application.dependency_overrides[get_db] = _override_get_db
    application.dependency_overrides[database_health_dependency] = lambda: True
    return application


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client bound to the ASGI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as http:
        yield http


def _create_user(
    factory: sessionmaker[Session],
    username: str,
    role: str,
    password: str = "Test1234",
) -> User:
    """Insert a user directly in the test database."""
    with factory() as session:
        user = User(
            username=username,
            email=f"{username}@test.local",
            full_name=username.capitalize(),
            hashed_password=hash_password(password),
            role=UserRole(role),
            is_active=True,
        )
        session.add(user)
        session.commit()
        return user


@pytest.fixture
def admin_user(session_factory: sessionmaker[Session]) -> User:
    """Create an admin user."""
    return _create_user(session_factory, "admin", UserRole.ADMIN)


@pytest.fixture
def cashier_user(session_factory: sessionmaker[Session]) -> User:
    """Create a cashier user."""
    return _create_user(session_factory, "cajero", UserRole.CASHIER)


@pytest.fixture
def waiter_user(session_factory: sessionmaker[Session]) -> User:
    """Create a waiter user."""
    return _create_user(session_factory, "mesero", UserRole.WAITER)


@pytest.fixture
def inactive_user(session_factory: sessionmaker[Session]) -> User:
    """Create a deactivated user."""
    user = _create_user(session_factory, "inactivo", UserRole.WAITER)
    with session_factory() as session:
        stored = session.get(User, user.id)
        assert stored is not None
        stored.is_active = False
        session.commit()
    return user


async def _login(client: AsyncClient, username: str, password: str = "Test1234") -> str:
    """Authenticate and return the access token."""
    response = await client.post(
        f"{API_PREFIX}/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200, response.text
    return str(response.json()["access_token"])


@pytest.fixture
async def admin_token(client: AsyncClient, admin_user: User) -> str:
    """Return an access token for the admin user."""
    return await _login(client, admin_user.username)


@pytest.fixture
async def cashier_token(client: AsyncClient, cashier_user: User) -> str:
    """Return an access token for the cashier user."""
    return await _login(client, cashier_user.username)


@pytest.fixture
async def waiter_token(client: AsyncClient, waiter_user: User) -> str:
    """Return an access token for the waiter user."""
    return await _login(client, waiter_user.username)


def auth_header(token: str) -> dict[str, str]:
    """Build the Authorization header for a token."""
    return {"Authorization": f"Bearer {token}"}
