from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import RoleEnum, User

TEST_ADMIN_EMAIL = "admin@test.com"
TEST_ADMIN_PASSWORD = "adminpass123"
TEST_WAITER_EMAIL = "mesero@test.com"
TEST_WAITER_PASSWORD = "meseropass123"


@pytest.fixture
def engine():
    """Motor SQLite en memoria, compartido entre sesiones."""
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


@pytest.fixture
def session(engine) -> Generator[Session, None, None]:
    """Sesión con las tablas creadas y datos iniciales."""
    Base.metadata.create_all(bind=engine)
    testing_session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    testing_session.add_all(
        [
            User(
                email=TEST_ADMIN_EMAIL,
                hashed_password=hash_password(TEST_ADMIN_PASSWORD),
                full_name="Admin Test",
                role=RoleEnum.ADMIN,
            ),
            User(
                email=TEST_WAITER_EMAIL,
                hashed_password=hash_password(TEST_WAITER_PASSWORD),
                full_name="Mesero Test",
                role=RoleEnum.WAITER,
            ),
        ]
    )
    testing_session.commit()

    yield testing_session

    testing_session.close()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(session) -> Generator[TestClient, None, None]:
    """TestClient de FastAPI con la dependencia de base de datos sustituida."""

    def override_get_db() -> Generator[Session, None, None]:
        yield session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_header(client) -> dict[str, str]:
    """Cabecera Authorization con el token del usuario administrador."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": TEST_ADMIN_EMAIL, "password": TEST_ADMIN_PASSWORD},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}
