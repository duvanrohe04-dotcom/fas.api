"""Product model."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.columns import created_at_column, money_type, updated_at_column

if TYPE_CHECKING:
    from app.models.category import Category
    from app.models.order_item import OrderItem

LOW_STOCK_THRESHOLD = 5


class Product(Base):
    """A sellable menu item with price and stock control."""

    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
        Index("ix_products_category_active", "category_id", "is_active"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(money_type(), nullable=False)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    stock: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    low_stock_threshold: Mapped[int] = mapped_column(
        Integer,
        default=LOW_STOCK_THRESHOLD,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = updated_at_column()

    category: Mapped[Category] = relationship(back_populates="products")
    order_items: Mapped[list[OrderItem]] = relationship(
        back_populates="product",
        passive_deletes=True,
    )

    @property
    def is_low_stock(self) -> bool:
        """True when the stock is at or below the configured threshold."""
        return self.stock <= self.low_stock_threshold

    @property
    def is_available(self) -> bool:
        """True when the product can be ordered right now."""
        return self.is_active and self.stock > 0

    def __repr__(self) -> str:
        """Return a readable representation for debugging."""
        return f"<Product id={self.id} name={self.name!r} stock={self.stock}>"
