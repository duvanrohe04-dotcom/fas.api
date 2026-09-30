"""Schemas for products."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from app.core.dates import as_utc

MONEY_PATTERN = r"^\d+(\.\d{1,2})?$"

PRODUCT_EXAMPLE = {
    "name": "Espresso doble",
    "description": "Doble carga de espresso de la casa.",
    "price": "2.80",
    "category_id": 1,
    "stock": 40,
    "low_stock_threshold": 10,
    "is_active": True,
}


class ProductBase(BaseModel):
    """Fields shared by create and update payloads."""

    name: str = Field(min_length=2, max_length=120, examples=["Espresso doble"])
    description: str | None = Field(
        default=None,
        max_length=500,
        examples=["Doble carga de espresso de la casa."],
    )
    category_id: int = Field(gt=0, examples=[1], description="Categoría a la que pertenece.")
    is_active: bool = Field(default=True, examples=[True])


class ProductCreate(ProductBase):
    """Payload to create a product."""

    price: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        examples=["2.80"],
        description="Precio unitario con dos decimales.",
    )
    stock: int = Field(default=0, ge=0, examples=[40])
    low_stock_threshold: int = Field(default=5, ge=0, examples=[10])

    model_config = ConfigDict(json_schema_extra={"examples": [PRODUCT_EXAMPLE]})


class ProductUpdate(BaseModel):
    """Partial payload to update a product."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"price": "3.10", "stock": 25},
                {"is_active": False},
            ]
        }
    )

    name: str | None = Field(default=None, min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    category_id: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(
        default=None,
        gt=0,
        max_digits=10,
        decimal_places=2,
    )
    stock: int | None = Field(default=None, ge=0)
    low_stock_threshold: int | None = Field(default=None, ge=0)
    is_active: bool | None = None

    @field_validator("price")
    @classmethod
    def _check_price(cls, value: Decimal | None) -> Decimal | None:
        """Reject prices with more than two decimal places."""
        if value is None:
            return None
        if value.as_tuple().exponent < -2:
            raise ValueError("El precio admite como máximo 2 decimales")
        return value


class ProductRead(BaseModel):
    """Product representation returned by the API."""

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "id": 1,
                "name": "Espresso doble",
                "description": "Doble carga de espresso de la casa.",
                "price": "2.80",
                "category_id": 1,
                "category_name": "Cafés",
                "stock": 40,
                "low_stock_threshold": 10,
                "is_active": True,
                "is_low_stock": False,
                "is_available": True,
                "created_at": "2026-01-05T10:00:00Z",
                "updated_at": "2026-01-05T10:00:00Z",
            }
        },
    )

    id: int = Field(examples=[1])
    name: str = Field(examples=["Espresso doble"])
    description: str | None = None
    price: Decimal = Field(examples=["2.80"])
    category_id: int = Field(examples=[1])
    category_name: str | None = Field(default=None, examples=["Cafés"])
    stock: int = Field(examples=[40])
    low_stock_threshold: int = Field(examples=[10])
    is_active: bool = Field(examples=[True])
    is_low_stock: bool = Field(description="True cuando el stock está en o bajo el umbral.")
    is_available: bool = Field(description="True cuando el producto está activo y con stock.")
    created_at: datetime
    updated_at: datetime

    @field_serializer("price")
    def _serialize_price(self, value: Decimal) -> str:
        """Render the price with exactly two decimals."""
        return f"{value:.2f}"

    @classmethod
    def from_model(cls, product: Any) -> ProductRead:
        """Build the response payload from an ORM product."""
        return cls(
            id=product.id,
            name=product.name,
            description=product.description,
            price=product.price,
            category_id=product.category_id,
            category_name=product.category.name if product.category is not None else None,
            stock=product.stock,
            low_stock_threshold=product.low_stock_threshold,
            is_active=product.is_active,
            is_low_stock=product.is_low_stock,
            is_available=product.is_available,
            created_at=as_utc(product.created_at),
            updated_at=as_utc(product.updated_at),
        )


class ProductStockUpdate(BaseModel):
    """Payload to adjust the stock of a product."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"quantity": 10, "reason": "recepción"}]}
    )

    quantity: int = Field(
        gt=0,
        examples=[10],
        description="Cantidad a sumar al stock actual.",
    )
    reason: str | None = Field(
        default=None,
        max_length=255,
        examples=["recepción de mercancía"],
    )
