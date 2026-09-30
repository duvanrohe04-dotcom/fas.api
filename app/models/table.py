"""Dining table model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.columns import created_at_column, updated_at_column

if TYPE_CHECKING:
    from app.models.order import Order


class Table(Base):
    """A physical table of the coffee shop."""

    __tablename__ = "tables"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(60), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    orders: Mapped[list[Order]] = relationship(
        back_populates="table",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        """Return a readable representation for debugging."""
        return f"<Table id={self.id} number={self.number}>"
