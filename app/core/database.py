"""Database engine, session factory and FastAPI dependencies."""

from __future__ import annotations

import logging
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from typing import Any

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


def build_engine(url: str | None = None, **kwargs: Any) -> Engine:
    """Create a SQLAlchemy engine tuned for the target database."""
    database_url = url or settings.DATABASE_URL
    options: dict[str, Any] = {
        "echo": settings.DATABASE_ECHO,
        "future": True,
        **kwargs,
    }
    if database_url.startswith("sqlite"):
        options["connect_args"] = {"check_same_thread": False}
    return create_engine(database_url, **options)


engine: Engine = build_engine()


SQLITE_PRAGMAS = (
    "PRAGMA foreign_keys=ON",
    "PRAGMA journal_mode=WAL",
)


def register_sqlite_pragma(target_engine: Engine) -> None:
    """Enable foreign keys and WAL on every new SQLite connection."""
    if target_engine.dialect.name != "sqlite":
        return

    @event.listens_for(target_engine, "connect")
    def _set_pragma(dbapi_connection: Any, _record: Any) -> None:
        cursor = dbapi_connection.cursor()
        try:
            for pragma in SQLITE_PRAGMAS:
                cursor.execute(pragma)
        finally:
            cursor.close()


register_sqlite_pragma(engine)


SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a session with rollback on error."""
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager for scripts and background tasks."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection(target_engine: Engine | None = None) -> bool:
    """Return True when the database answers a trivial query."""
    from sqlalchemy import text

    try:
        with (target_engine or engine).connect() as connection:
            connection.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError:
        logger.warning("Database health check failed", exc_info=True)
        return False


def database_health_dependency() -> bool:
    """FastAPI dependency wrapping :func:`check_connection`."""
    return check_connection()


def init_database(target_engine: Engine | None = None) -> None:
    """Create all tables declared on the metadata."""
    from app.db.base import Base

    Base.metadata.create_all(bind=target_engine or engine)
    logger.info("Database schema ready")
