"""Order model and its lifecycle rules."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.dates import ZERO
from app.db.base import Base
from app.models.columns import money_type

if TYPE_CHECKING:
    from app.models.customer import Customer
    from app.models.order_item import OrderItem
    from app.models.payment import Payment
    from app.models.table import Table
    from app.models.user import User


class OrderStatus(enum.StrEnum):
    """Lifecycle of an order."""

    PENDING = "pendiente"
    PREPARING = "preparando"
    READY = "listo"
    DELIVERED = "entregado"
    CANCELLED = "cancelado"


ALLOWED_TRANSITIONS: dict[OrderStatus, frozenset[OrderStatus]] = {
    OrderStatus.PENDING: frozenset({OrderStatus.PREPARING, OrderStatus.CANCELLED}),
    OrderStatus.PREPARING: frozenset({OrderStatus.READY, OrderStatus.CANCELLED}),
    OrderStatus.READY: frozenset({OrderStatus.DELIVERED}),
    OrderStatus.DELIVERED: frozenset(),
    OrderStatus.CANCELLED: frozenset(),
}

OPEN_STATUSES: tuple[OrderStatus, ...] = (
    OrderStatus.PENDING,
    OrderStatus.PREPARING,
    OrderStatus.READY,
)

ACTIVE_TABLE_STATUSES: tuple[OrderStatus, ...] = (
    OrderStatus.PENDING,
    OrderStatus.PREPARING,
    OrderStatus.READY,
)


def enum_values(enum_class: type[enum.Enum]) -> list[str]:
    """Return the string values of an enum, honouring value_callable overrides."""
    return [member.value for member in enum_class]


class Order(Base):
    """A customer order with its lines and payments."""

    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("total >= 0", name="ck_orders_total_non_negative"),
        CheckConstraint("paid_amount >= 0", name="ck_orders_paid_non_negative"),
        Index("ix_orders_status_created", "status", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        index=True,
    )
    table_id: Mapped[int | None] = mapped_column(
        ForeignKey("tables.id", ondelete="SET NULL"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[OrderStatus] = mapped_column(
        Enum(
            OrderStatus,
            native_enum=False,
            length=20,
            validate_strings=True,
            values_callable=enum_values,
        ),
        default=OrderStatus.PENDING,
        nullable=False,
        index=True,
    )
    subtotal: Mapped[Decimal] = mapped_column(
        money_type(), default=ZERO, server_default="0", nullable=False
    )
    discount: Mapped[Decimal] = mapped_column(
        money_type(), default=ZERO, server_default="0", nullable=False
    )
    tax: Mapped[Decimal] = mapped_column(
        money_type(), default=ZERO, server_default="0", nullable=False
    )
    total: Mapped[Decimal] = mapped_column(
        money_type(), default=ZERO, server_default="0", nullable=False
    )
    paid_amount: Mapped[Decimal] = mapped_column(
        money_type(), default=ZERO, server_default="0", nullable=False
    )
    notes: Mapped[str | None] = mapped_column(Text)
    cancelled_reason: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    items: Mapped[list[OrderItem]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="OrderItem.id",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="order",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Payment.id",
    )
    customer: Mapped[Customer] = relationship(back_populates="orders")
    table: Mapped[Table] = relationship(back_populates="orders")
    user: Mapped[User] = relationship()

    @property
    def balance_due(self) -> Decimal:
        """Amount still pending for this order."""
        return max(ZERO, self.total - self.paid_amount)

    @property
    def is_paid(self) -> bool:
        """True when the payments cover the whole total."""
        return self.total > ZERO and self.paid_amount >= self.total

    def can_transition_to(self, new_status: OrderStatus) -> bool:
        """Check whether the status change is allowed."""
        return new_status in ALLOWED_TRANSITIONS.get(self.status, frozenset())

    def next_statuses(self) -> list[OrderStatus]:
        """Return the statuses reachable from the current one."""
        return sorted(ALLOWED_TRANSITIONS.get(self.status, frozenset()), key=lambda s: s.value)

    def __repr__(self) -> str:
        """Return a readable representation for debugging."""
        return f"<Order id={self.id} code={self.code!r} status={self.status}>"
