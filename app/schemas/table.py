"""Schemas for dining tables."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.dates import as_utc

TABLE_EXAMPLE = {
    "number": 1,
    "name": "Ventana",
    "capacity": 4,
    "is_active": True,
}


class TableCreate(BaseModel):
    """Payload to register a table."""

    model_config = ConfigDict(json_schema_extra={"examples": [TABLE_EXAMPLE]})

    number: int = Field(gt=0, le=999, examples=[1])
    name: str = Field(min_length=2, max_length=60, examples=["Ventana"])
    capacity: int = Field(default=4, ge=1, le=20, examples=[4])
    is_active: bool = Field(default=True, examples=[True])


class TableUpdate(BaseModel):
    """Partial payload to update a table."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"capacity": 6}, {"is_active": False}]}
    )

    number: int | None = Field(default=None, gt=0, le=999)
    name: str | None = Field(default=None, min_length=2, max_length=60)
    capacity: int | None = Field(default=None, ge=1, le=20)
    is_active: bool | None = None


class TableRead(BaseModel):
    """Table representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    number: int = Field(examples=[1])
    name: str = Field(examples=["Ventana"])
    capacity: int = Field(examples=[4])
    is_active: bool = Field(examples=[True])
    is_occupied: bool = Field(
        default=False,
        description="True cuando la mesa tiene al menos un pedido abierto.",
    )
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, table: Any) -> TableRead:
        """Build the response payload from an ORM table."""
        return cls(
            id=table.id,
            number=table.number,
            name=table.name,
            capacity=table.capacity,
            is_active=table.is_active,
            is_occupied=bool(getattr(table, "is_occupied", False)),
            created_at=as_utc(table.created_at),
            updated_at=as_utc(table.updated_at),
        )
