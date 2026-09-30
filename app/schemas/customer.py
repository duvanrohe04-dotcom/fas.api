"""Schemas for customers."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.core.dates import as_utc

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$"
PHONE_PATTERN = r"^[0-9+()\-\s]{6,30}$"

CUSTOMER_EXAMPLE = {
    "name": "Lucía Fernández",
    "email": "lucia@example.com",
    "phone": "+34 600 123 456",
    "is_active": True,
}


class CustomerBase(BaseModel):
    """Fields shared by the customer payloads."""

    model_config = ConfigDict(json_schema_extra={"examples": [CUSTOMER_EXAMPLE]})

    name: str = Field(min_length=2, max_length=120, examples=["Lucía Fernández"])
    email: str | None = Field(
        default=None,
        max_length=120,
        pattern=EMAIL_PATTERN,
        examples=["lucia@example.com"],
    )
    phone: str | None = Field(
        default=None,
        max_length=30,
        pattern=PHONE_PATTERN,
        examples=["+34 600 123 456"],
    )


class CustomerCreate(CustomerBase):
    """Payload to register a customer."""

    is_active: bool = Field(default=True, examples=[True])


class CustomerUpdate(BaseModel):
    """Partial payload to update a customer."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"email": "lucia.nuevo@example.com"}, {"is_active": False}]}
    )

    name: str | None = Field(default=None, min_length=2, max_length=120)
    email: str | None = Field(default=None, max_length=120, pattern=EMAIL_PATTERN)
    phone: str | None = Field(default=None, max_length=30, pattern=PHONE_PATTERN)
    is_active: bool | None = None


class CustomerRead(BaseModel):
    """Customer representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    name: str = Field(examples=["Lucía Fernández"])
    email: str | None = None
    phone: str | None = None
    is_active: bool = Field(examples=[True])
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, customer: Any) -> CustomerRead:
        """Build the response payload from an ORM customer."""
        return cls(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone=customer.phone,
            is_active=customer.is_active,
            created_at=as_utc(customer.created_at),
            updated_at=as_utc(customer.updated_at),
        )
