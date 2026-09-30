"""Payment model."""

from __future__ import annotations

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.columns import money_type
from app.models.order import enum_values

if TYPE_CHECKING:
    from app.models.order import Order
    from app.models.user import User


class PaymentMethod(enum.StrEnum):
    """Available ways of paying for an order."""

    CASH = "efectivo"
    CARD = "tarjeta"
    TRANSFER = "transferencia"


class Payment(Base):
    """A payment registered against an order."""

    __tablename__ = "payments"
    __table_args__ = (Index("ix_payments_method_created", "method", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    method: Mapped[PaymentMethod] = mapped_column(
        Enum(
            PaymentMethod,
            native_enum=False,
            length=20,
            validate_strings=True,
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(money_type(), nullable=False)
    reference: Mapped[str | None] = mapped_column(
        String(80),
        doc="Card authorization code or bank reference.",
    )
    notes: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    order: Mapped[Order] = relationship(back_populates="payments")
    user: Mapped[User] = relationship()

    def __repr__(self) -> str:
        """Return a readable representation for debugging."""
        return f"<Payment id={self.id} order={self.order_id} amount={self.amount}>"
