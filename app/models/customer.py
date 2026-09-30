"""Customer model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.columns import created_at_column, updated_at_column

if TYPE_CHECKING:
    from app.models.order import Order


class Customer(Base):
    """A registered customer who can place orders."""

    __tablename__ = "customers"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), unique=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(30), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    orders: Mapped[list[Order]] = relationship(
        back_populates="customer",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return a readable representation for debugging."""
        return f"<Customer id={self.id} name={self.name!r}>"
