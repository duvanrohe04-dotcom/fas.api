"""Reusable column types for the ORM models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import DateTime, Numeric, TypeDecorator, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.dates import quantize_money, utcnow


class MoneyType(TypeDecorator[Decimal]):
    """Monetary column that always stores and returns two decimal places."""

    impl = Numeric
    cache_ok = True

    def __init__(self, precision: int = 12, scale: int = 2) -> None:
        """Configure the underlying numeric precision and scale."""
        super().__init__(precision=precision, scale=scale)

    def process_bind_param(self, value: Any, dialect: Any) -> Decimal | None:
        """Quantize the value before it reaches the database."""
        if value is None:
            return None
        return quantize_money(value)

    def process_result_value(self, value: Any, dialect: Any) -> Decimal | None:
        """Quantize the value coming back from the database."""
        if value is None:
            return None
        return quantize_money(value)

    def process_literal_param(self, value: Any, dialect: Any) -> str:
        """Render the value as a literal for inline SQL."""
        return str(quantize_money(value))


def money_type() -> MoneyType:
    """Return a fresh money column type instance."""
    return MoneyType(precision=12, scale=2)


def created_at_column() -> Mapped[datetime]:
    """Build the column storing the creation timestamp."""
    return mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        server_default=func.now(),
        nullable=False,
        index=True,
    )


def updated_at_column() -> Mapped[datetime]:
    """Build the column storing the last update timestamp."""
    return mapped_column(
        DateTime(timezone=True),
        default=utcnow,
        onupdate=utcnow,
        server_default=func.now(),
        nullable=False,
    )
