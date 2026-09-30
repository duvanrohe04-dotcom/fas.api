"""Declarative base shared by every model."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Common declarative base for all ORM models."""

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict of the mapped columns."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}
