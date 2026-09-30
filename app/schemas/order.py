"""Schemas for orders, their lines and the kitchen board."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_serializer

from app.core.dates import ZERO, as_utc
from app.models import OrderStatus

STATUS_LABELS: dict[OrderStatus, str] = {
    OrderStatus.PENDING: "Pendiente",
    OrderStatus.PREPARING: "En preparación",
    OrderStatus.READY: "Listo para servir",
    OrderStatus.DELIVERED: "Entregado",
    OrderStatus.CANCELLED: "Cancelado",
}

ORDER_EXAMPLE = {
    "items": [{"product_id": 1, "quantity": 2, "notes": "sin azúcar"}],
    "customer_id": 1,
    "table_id": 1,
    "discount": "0.00",
    "tax": "0.21",
    "notes": "Para llevar",
}


class OrderItemCreate(BaseModel):
    """A product line requested by the client."""

    model_config = ConfigDict(
        json_schema_extra={"examples": [{"product_id": 1, "quantity": 2, "notes": "sin azúcar"}]}
    )

    product_id: int = Field(gt=0, examples=[1])
    quantity: int = Field(gt=0, le=100, examples=[2], description="Unidades solicitadas.")
    notes: str | None = Field(default=None, max_length=255, examples=["sin azúcar"])


class OrderCreate(BaseModel):
    """Payload to create an order; prices and totals are computed server side."""

    model_config = ConfigDict(json_schema_extra={"examples": [ORDER_EXAMPLE]})

    items: list[OrderItemCreate] = Field(
        min_length=1,
        max_length=50,
        description="Líneas del pedido. Los precios se toman del catálogo.",
    )
    customer_id: int | None = Field(default=None, gt=0)
    table_id: int | None = Field(default=None, gt=0)
    discount: Decimal = Field(
        default=ZERO,
        ge=0,
        max_digits=10,
        decimal_places=2,
        examples=["0.00"],
        description="Descuento aplicado sobre el subtotal.",
    )
    tax: Decimal = Field(
        default=ZERO,
        ge=0,
        max_digits=10,
        decimal_places=2,
        examples=["0.21"],
    )
    notes: str | None = Field(default=None, max_length=500, examples=["Para llevar"])


class OrderStatusUpdate(BaseModel):
    """Payload to move an order to another status."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {"status": "preparando"},
                {"status": "cancelado", "reason": "el cliente se fue"},
            ]
        }
    )

    status: OrderStatus = Field(description="Nuevo estado del pedido.")
    reason: str | None = Field(
        default=None,
        max_length=255,
        description="Motivo obligatorio cuando el nuevo estado es 'cancelado'.",
    )


class OrderCancel(BaseModel):
    """Payload to cancel an order."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"reason": "el cliente se fue"}]})

    reason: str = Field(min_length=3, max_length=255, examples=["el cliente se fue"])


class OrderItemRead(BaseModel):
    """Line of an order as returned by the API."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    product_id: int = Field(examples=[1])
    product_name: str = Field(examples=["Espresso doble"])
    unit_price: Decimal = Field(examples=["2.80"])
    quantity: int = Field(examples=[2])
    subtotal: Decimal = Field(examples=["5.60"])
    notes: str | None = None

    @field_serializer("unit_price", "subtotal")
    def _serialize_money(self, value: Decimal) -> str:
        """Render money amounts with exactly two decimals."""
        return f"{value:.2f}"


class OrderSummaryRead(BaseModel):
    """Lightweight order representation used by listings."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(examples=[1])
    code: str = Field(examples=["PED-000001"])
    status: OrderStatus = Field(examples=["pendiente"])
    status_label: str = Field(examples=["Pendiente"])
    total: Decimal = Field(examples=["5.81"])
    item_count: int = Field(examples=[2], description="Número de líneas del pedido.")
    customer_id: int | None = None
    customer_name: str | None = None
    table_id: int | None = None
    table_number: int | None = None
    username: str | None = None
    created_at: datetime

    @field_serializer("total")
    def _serialize_money(self, value: Decimal) -> str:
        """Render money amounts with exactly two decimals."""
        return f"{value:.2f}"

    @classmethod
    def from_model(cls, order: Any) -> OrderSummaryRead:
        """Build the summary payload from an ORM order."""
        return cls(
            id=order.id,
            code=order.code,
            status=order.status,
            status_label=STATUS_LABELS.get(order.status, order.status.value),
            total=order.total,
            item_count=len(order.items),
            customer_id=order.customer_id,
            customer_name=order.customer.name if order.customer is not None else None,
            table_id=order.table_id,
            table_number=order.table.number if order.table is not None else None,
            username=order.user.username if order.user is not None else None,
            created_at=as_utc(order.created_at),
        )


class OrderRead(OrderSummaryRead):
    """Full order representation returned by the API."""

    subtotal: Decimal = Field(examples=["5.60"])
    discount: Decimal = Field(examples=["0.00"])
    tax: Decimal = Field(examples=["0.21"])
    paid_amount: Decimal = Field(examples=["0.00"])
    balance_due: Decimal = Field(examples=["5.81"])
    is_paid: bool = Field(examples=[False])
    notes: str | None = None
    cancelled_reason: str | None = None
    allowed_transitions: list[OrderStatus] = Field(
        default_factory=list,
        description="Estados alcanzables desde el estado actual.",
    )
    updated_at: datetime
    delivered_at: datetime | None = None
    items: list[OrderItemRead] = Field(default_factory=list)

    @field_serializer("subtotal", "discount", "tax", "paid_amount", "balance_due")
    def _serialize_order_money(self, value: Decimal) -> str:
        """Render money amounts with exactly two decimals."""
        return f"{value:.2f}"

    @classmethod
    def from_model(cls, order: Any) -> OrderRead:
        """Build the full payload from an ORM order."""
        base = OrderSummaryRead.from_model(order)
        return cls(
            **base.model_dump(),
            subtotal=order.subtotal,
            discount=order.discount,
            tax=order.tax,
            paid_amount=order.paid_amount,
            balance_due=order.balance_due,
            is_paid=order.is_paid,
            notes=order.notes,
            cancelled_reason=order.cancelled_reason,
            allowed_transitions=order.next_statuses(),
            updated_at=as_utc(order.updated_at),
            delivered_at=as_utc(order.delivered_at),
            items=[OrderItemRead.model_validate(item) for item in order.items],
        )


class KitchenOrderRead(OrderSummaryRead):
    """Order card shown in the kitchen board."""

    items: list[OrderItemRead] = Field(default_factory=list)

    @classmethod
    def from_model(cls, order: Any) -> KitchenOrderRead:
        """Build the kitchen card from an ORM order."""
        base = OrderSummaryRead.from_model(order)
        return cls(
            **base.model_dump(),
            items=[OrderItemRead.model_validate(item) for item in order.items],
        )
