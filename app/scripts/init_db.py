"""Inicializa la base de datos al arrancar el contenedor.

Crea el esquema y, si no existe ningún usuario, el administrador inicial.
Ambas operaciones son idempotentes: se pueden repetir en cada arranque.

Se controla con las variables de entorno:
    ADMIN_EMAIL: email del administrador inicial (opcional).
    ADMIN_PASSWORD: contraseña del administrador inicial (opcional).
    DB_WAIT_SECONDS: segundos de espera a que la base de datos acepte conexiones.

Si no se definen ADMIN_EMAIL y ADMIN_PASSWORD, el esquema se crea igualmente
y el arranque continúa; hay que crear el admin a mano.
"""

from __future__ import annotations

import logging
import os
import sys
import time

from sqlalchemy import inspect, text
from sqlalchemy.exc import OperationalError

from app.core.database import Base, SessionLocal, engine

# Importar app.models registra todas las tablas en Base.metadata.
from app.models import RoleEnum
from app.schemas.auth import UserCreate
from app.scripts.seed_demo import seed_demo_data
from app.services.auth_service import create_user_if_empty

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger("init_db")

DEFAULT_DB_WAIT_SECONDS = 30


def wait_for_database() -> None:
    """Espera a que la base de datos acepte conexiones."""
    timeout = int(os.getenv("DB_WAIT_SECONDS", DEFAULT_DB_WAIT_SECONDS))
    deadline = time.monotonic() + timeout

    while True:
        try:
            with engine.connect():
                return
        except OperationalError as exc:
            if time.monotonic() >= deadline:
                logger.error("La base de datos no respondió en %ss: %s", timeout, exc)
                raise
            logger.info("Esperando a la base de datos...")
            time.sleep(2)


def create_schema() -> None:
    """Crea las tablas que falten. No modifica las existentes."""
    Base.metadata.create_all(bind=engine)
    add_missing_columns()
    logger.info("Esquema verificado (%s tablas)", len(Base.metadata.tables))


def add_missing_columns() -> None:
    """Añade columnas nuevas (nullable) a tablas ya existentes.

    `create_all` no altera tablas creadas antes de que existiera la columna.
    Solo cubre columnas opcionales; cambios mayores requieren Alembic.
    """
    inspector = inspect(engine)
    for table in Base.metadata.sorted_tables:
        existing = {col["name"] for col in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name in existing or not column.nullable:
                continue
            column_type = column.type.compile(dialect=engine.dialect)
            with engine.begin() as conn:
                conn.execute(
                    text(
                        f'ALTER TABLE "{table.name}" '
                        f'ADD COLUMN "{column.name}" {column_type}'
                    )
                )
            logger.info("Columna añadida: %s.%s", table.name, column.name)

        # `create_all` tampoco crea los índices de tablas que ya existían.
        for index in table.indexes:
            index.create(bind=engine, checkfirst=True)


def create_initial_admin() -> None:
    """Crea el administrador inicial si la tabla de usuarios está vacía."""
    email = os.getenv("ADMIN_EMAIL")
    password = os.getenv("ADMIN_PASSWORD")

    session = SessionLocal()
    try:
        if not email or not password:
            logger.info(
                "ADMIN_EMAIL/ADMIN_PASSWORD no definidos. Crea el administrador con: "
                "python -m app.scripts.create_admin --email <email> --password <clave>"
            )
            return

        user = create_user_if_empty(
            session,
            UserCreate(
                email=email,
                password=password,
                full_name=os.getenv("ADMIN_FULL_NAME", "Administrador"),
                role=RoleEnum.ADMIN,
            ),
        )

        if user is None:
            logger.info("Ya existen usuarios: no se crea el administrador inicial.")
        else:
            logger.info("Administrador inicial creado: %s", user.email)
    finally:
        session.close()


def load_demo_data() -> None:
    """Carga el menú de ejemplo si `SEED_DEMO_DATA` está activo y la base está vacía."""
    if os.getenv("SEED_DEMO_DATA", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "si",
    }:
        return

    session = SessionLocal()
    try:
        seed_demo_data(session)
    finally:
        session.close()


def main() -> int:
    """Punto de entrada. Devuelve un código de salida para el contenedor."""
    try:
        wait_for_database()
        create_schema()
        create_initial_admin()
        load_demo_data()
    except Exception:
        logger.exception("Fallo al inicializar la base de datos")
        return 1

    logger.info("Base de datos lista")
    return 0


if __name__ == "__main__":
    sys.exit(main())
