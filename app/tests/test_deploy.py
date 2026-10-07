"""Comprobaciones pensadas para el despliegue: migración ligera y CORS."""

from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.core.config import Settings
from app.core.database import Base
from app.scripts import init_db


def test_init_db_actualiza_una_base_antigua(tmp_path: Path, monkeypatch):
    """Una tabla creada antes de existir las columnas nuevas queda al día."""
    engine = create_engine(f"sqlite:///{tmp_path / 'antigua.db'}")
    with engine.begin() as conn:
        conn.execute(
            text(
                "CREATE TABLE orders ("
                "id INTEGER PRIMARY KEY, total_amount FLOAT NOT NULL, "
                "status VARCHAR(10) NOT NULL, table_id INTEGER, waiter_id INTEGER, "
                "created_at DATETIME, updated_at DATETIME)"
            )
        )
    monkeypatch.setattr(init_db, "engine", engine)

    Base.metadata.create_all(bind=engine)
    init_db.add_missing_columns()
    # Repetirlo no debe fallar: es idempotente.
    init_db.add_missing_columns()

    inspector = inspect(engine)
    columns = {c["name"] for c in inspector.get_columns("orders")}
    assert {"order_type", "customer_name", "notes", "tracking_code"} <= columns
    indexed = {c for i in inspector.get_indexes("orders") for c in i["column_names"]}
    assert "tracking_code" in indexed


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("*", ["*"]),
        ("", ["*"]),
        ("https://a.com", ["https://a.com"]),
        (" https://a.com/ , https://b.com ", ["https://a.com", "https://b.com"]),
    ],
)
def test_cors_origins_se_interpreta_bien(raw: str, expected: list[str]):
    settings = Settings(SECRET_KEY="x", DATABASE_URL="sqlite://", CORS_ORIGINS=raw)

    assert settings.cors_origins_list == expected
