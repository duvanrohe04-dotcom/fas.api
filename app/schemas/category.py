"""Schemas for menu categories."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.dates import as_utc

CATEGORY_EXAMPLE = {
    "name": "Cafés",
    "description": "Café de grano, espresso y técnicas de specialty.",
    "is_active": True,
}


def _normalize_name(value: str | None) -> str | None:
    """Collapse extra whitespace in the category name."""
    if value is None:
        return None
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("El nombre no puede estar vacío")
    return normalized


class CategoryBase(BaseModel):
    """Fields shared by create and update payloads."""

    name: str = Field(min_length=2, max_length=80, examples=["Cafés"])
    description: str | None = Field(
        default=None,
        max_length=255,
        examples=["Café de grano, espresso y técnicas de specialty."],
    )
    is_active: bool = Field(default=True, examples=[True])

    _normalize_name = field_validator("name")(_normalize_name)


class CategoryCreate(CategoryBase):
    """Payload to create a category."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                CATEGORY_EXAMPLE,
                {
                    "name": "Bebidas frías",
                    "description": "Smoothies, jugos y limonadas.",
                    "is_active": True,
                },
            ]
        }
    )


class CategoryUpdate(BaseModel):
    """Partial payload to update a category."""

    model_config = ConfigDict(
        json_schema_extra={"example": {"description": "Nueva descripción", "is_active": False}}
    )

    name: str | None = Field(default=None, min_length=2, max_length=80)
    description: str | None = Field(default=None, max_length=255)
    is_active: bool | None = None

    _normalize_name = field_validator("name")(_normalize_name)


class CategoryRead(BaseModel):
    """Category representation returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Cafés",
                "slug": "cafes",
                "description": "Café de grano, espresso y técnicas de specialty.",
                "is_active": True,
                "product_count": 4,
                "created_at": "2026-01-05T10:00:00Z",
                "updated_at": "2026-01-05T10:00:00Z",
            }
        },
    )

    id: int = Field(examples=[1])
    name: str = Field(examples=["Cafés"])
    slug: str = Field(examples=["cafes"])
    description: str | None = None
    is_active: bool = Field(examples=[True])
    product_count: int | None = Field(
        default=None,
        description="Número de productos de la categoría; se rellena bajo demanda.",
    )
    created_at: datetime = Field(description="Fecha de creación en UTC.")
    updated_at: datetime = Field(description="Última actualización en UTC.")

    @classmethod
    def from_model(cls, category: Any, *, product_count: int | None = None) -> CategoryRead:
        """Build the response payload from an ORM category."""
        return cls(
            id=category.id,
            name=category.name,
            slug=category.slug,
            description=category.description,
            is_active=category.is_active,
            product_count=product_count,
            created_at=as_utc(category.created_at),
            updated_at=as_utc(category.updated_at),
        )
