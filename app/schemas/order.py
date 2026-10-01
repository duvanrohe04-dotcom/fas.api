from pydantic import BaseModel, ConfigDict, Field

from app.models import OrderStatus, PaymentMethod


class OrderItemCreate(BaseModel):
    """Línea a añadir a un pedido."""

    product_id: int
    quantity: int = Field(ge=1)


class OrderCreate(BaseModel):
    """Datos para crear un pedido."""

    table_id: int | None = None
    items: list[OrderItemCreate] = Field(min_length=1)


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
    waiter_id: int | None
    status: OrderStatus
    total_amount: float
    items: list[OrderItemRead]


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
