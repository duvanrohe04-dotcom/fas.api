"""Date and money helpers."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0.00")


def utcnow() -> datetime:
    """Return the current time as a timezone aware UTC datetime."""
    return datetime.now(UTC)


def as_utc(value: datetime | None) -> datetime | None:
    """Attach UTC to naive datetimes coming from SQLite."""
    if value is None:
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value


def quantize_money(value: Decimal | float | int | str) -> Decimal:
    """Round an amount to two decimal places using half-up rounding."""
    return Decimal(str(value)).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def to_decimal(value: Decimal | float | int | str) -> Decimal:
    """Convert any numeric input into a quantized Decimal."""
    return quantize_money(value)


def start_of_day(day: date) -> datetime:
    """Midnight UTC of the given day."""
    return datetime.combine(day, datetime.min.time(), tzinfo=UTC)


def end_of_day(day: date) -> datetime:
    """Last microsecond of the given day in UTC."""
    return datetime.combine(day, datetime.max.time(), tzinfo=UTC)
