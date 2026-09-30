"""Schemas for payments."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.dates import as_utc
from app.models import PaymentMethod

PAYMENT_EXAMPLE = {
    "order_id": 1,
    "method": "efectivo",
    "amount": "5.50",
    "reference": None,
    "notes": "pago en caja",
}


class PaymentCreate(BaseModel):
    """Payload to register a payment against an order."""

    model_config = ConfigDict(json_schema_extra={"examples": [PAYMENT_EXAMPLE]})

    order_id: int = Field(gt=0, examples=[1])
    method: PaymentMethod = Field(examples=["efectivo"])
    amount: Decimal = Field(
        gt=0,
        max_digits=10,
        decimal_places=2,
        examples=["5.50"],
        description="Importe del pago. No puede superar el saldo pendiente del pedido.",
    )
    reference: str | None = Field(
        default=None,
        max_length=80,
        examples=["AUTH-9931"],
        description="Código de autorización en tarjeta o referencia bancaria.",
    )
    notes: str | None = Field(default=None, max_length=255, examples=["pago en caja"])


class PaymentRead(BaseModel):
    """Payment representation returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    order_id: int = Field(examples=[1])
    order_code: str | None = Field(default=None, examples=["PED-000001"])
    method: PaymentMethod = Field(examples=["efectivo"])
    amount: Decimal = Field(examples=["5.50"])
    reference: str | None = None
    notes: str | None = None
    username: str | None = Field(default=None, examples=["cajero"])
    order_paid_amount: Decimal | None = Field(
        default=None,
        examples=["5.50"],
        description="Total pagado del pedido tras registrar este pago.",
    )
    order_balance_due: Decimal | None = Field(
        default=None,
        examples=["0.00"],
        description="Saldo pendiente del pedido tras registrar este pago.",
    )
    created_at: datetime

    @field_serializer("amount", "order_paid_amount", "order_balance_due")
    def _serialize_money(self, value: Decimal | None) -> str | None:
        """Render money amounts with exactly two decimals."""
        return None if value is None else f"{value:.2f}"

    @classmethod
    def from_model(cls, payment: Any) -> PaymentRead:
        """Build the response payload from an ORM payment."""
        order = payment.order
        return cls(
            id=payment.id,
            order_id=payment.order_id,
            order_code=order.code if order is not None else None,
            method=payment.method,
            amount=payment.amount,
            reference=payment.reference,
            notes=payment.notes,
            username=payment.user.username if payment.user is not None else None,
            order_paid_amount=order.paid_amount if order is not None else None,
            order_balance_due=order.balance_due if order is not None else None,
            created_at=as_utc(payment.created_at),
        )