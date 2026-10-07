from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import OrderStatus, PaymentMethod

OrderType = Literal["mesa", "llevar"]


class OrderItemCreate(BaseModel):
    """Línea a añadir a un pedido."""

    product_id: int
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    """Datos para crear un pedido."""

    table_id: int | None = None
    order_type: OrderType | None = None
    customer_name: str | None = Field(default=None, max_length=100)
    notes: str | None = Field(default=None, max_length=300)
    items: list[OrderItemCreate] = Field(min_length=1)

    @model_validator(mode="after")
    def _normalize_type(self) -> "OrderCreate":
        """Deduce el tipo si falta y exige mesa cuando el pedido es para mesa."""
        if self.order_type is None:
            self.order_type = "mesa" if self.table_id is not None else "llevar"
        if self.order_type == "mesa" and self.table_id is None:
            raise ValueError("Indica la mesa para un pedido en mesa")
        if self.order_type == "llevar":
            self.table_id = None
        self.customer_name = (self.customer_name or "").strip() or None
        self.notes = (self.notes or "").strip() or None
        return self


class OrderItemsAdd(BaseModel):
    """Líneas a añadir a un pedido existente."""

    items: list[OrderItemCreate] = Field(min_length=1)


class OrderStatusUpdate(BaseModel):
    """Cambio de estado de un pedido."""

    status: OrderStatus


class OrderItemRead(BaseModel):
    """Línea de pedido devuelta por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    quantity: int
    unit_price: float
    subtotal: float


class OrderRead(BaseModel):
    """Pedido devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    table_id: int | None
    table_number: int | None
    waiter_id: int | None
    order_type: str | None
    customer_name: str | None
    notes: str | None
    tracking_code: str | None
    status: OrderStatus
    total_amount: float
    is_paid: bool
    created_at: datetime | None = None
    items: list[OrderItemRead]


class OrderTrackRead(BaseModel):
    """Vista pública mínima para que el cliente siga su pedido."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: OrderStatus
    order_type: str | None
    table_number: int | None
    customer_name: str | None
    total_amount: float
    created_at: datetime | None = None


class OrdersSummary(BaseModel):
    """Resumen operativo del día para el panel."""

    pending: int
    active: int
    orders_today: int
    sales_today: float
    awaiting_payment: int


class PaymentCreate(BaseModel):
    """Datos para registrar el pago de un pedido."""

    method: PaymentMethod
    amount: float = Field(gt=0)


class PaymentRead(BaseModel):
    """Pago devuelto por la API."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    amount: float
    method: PaymentMethod


class OrderWithPaymentRead(OrderRead):
    """Pedido junto a su pago, si ya está pagado."""

    payment: PaymentRead | None = None
