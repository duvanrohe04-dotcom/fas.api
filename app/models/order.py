import enum
from typing import TYPE_CHECKING

from sqlalchemy import Enum, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.product import Product
    from app.models.table import Table
    from app.models.user import User


class OrderStatus(str, enum.Enum):
    PENDING = "pendiente"
    PREPARING = "preparando"
    READY = "listo"
    DELIVERED = "entregado"
    CANCELLED = "cancelado"


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    total_amount: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    status: Mapped[OrderStatus] = mapped_column(
        Enum(OrderStatus), default=OrderStatus.PENDING, nullable=False
    )

    # "mesa" (se sirve en una mesa) o "llevar" (se recoge en el mostrador).
    order_type: Mapped[str | None] = mapped_column(String(10))
    customer_name: Mapped[str | None] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(String(300))
    # Código aleatorio con el que el cliente consulta su pedido sin sesión.
    tracking_code: Mapped[str | None] = mapped_column(String(12), index=True)

    table_id: Mapped[int | None] = mapped_column(ForeignKey("tables.id"))
    waiter_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))

    table: Mapped["Table"] = relationship("Table", back_populates="orders")
    waiter: Mapped["User"] = relationship("User")
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem", back_populates="order", cascade="all, delete-orphan"
    )
    payment: Mapped["Payment"] = relationship(
        "Payment", back_populates="order", uselist=False
    )

    @property
    def table_number(self) -> int | None:
        """Número visible de la mesa, si el pedido es para una mesa."""
        return self.table.number if self.table is not None else None

    @property
    def is_paid(self) -> bool:
        """Indica si el pedido ya tiene un pago registrado."""
        return self.payment is not None


class OrderItem(Base, TimestampMixin):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    unit_price: Mapped[float] = mapped_column(Float, nullable=False)
    subtotal: Mapped[float] = mapped_column(Float, nullable=False)

    order: Mapped["Order"] = relationship("Order", back_populates="items")
    product: Mapped["Product"] = relationship("Product")
