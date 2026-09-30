"""Product data access layer."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Category, Product
from app.repositories.base import (
    ListQuery,
    apply_pagination,
    apply_search,
    build_page,
    count_statement,
)
from app.schemas.common import Page


class ProductRepository:
    """CRUD and listing operations for products."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def get(self, product_id: int) -> Product | None:
        """Fetch a single product by primary key."""
        return self.session.get(Product, product_id)

    def get_with_category(self, product_id: int) -> Product | None:
        """Fetch a product and eagerly load its category."""
        return self.session.execute(
            select(Product).where(Product.id == product_id)
        ).scalar_one_or_none()

    def list(
        self,
        query: ListQuery,
        *,
        category_id: int | None = None,
        is_active: bool | None = None,
        low_stock: bool | None = None,
    ) -> Page[Product]:
        """Return a paginated list of products with optional filters."""
        statement = select(Product)
        if category_id is not None:
            statement = statement.where(Product.category_id == category_id)
        if is_active is not None:
            statement = statement.where(Product.is_active.is_(is_active))
        if low_stock is True:
            statement = statement.where(Product.stock <= Product.low_stock_threshold)
        elif low_stock is False:
            statement = statement.where(Product.stock > Product.low_stock_threshold)
        statement = apply_search(statement, query, Product.name)
        total = self.session.execute(count_statement(statement)).scalar_one()
        statement = apply_pagination(statement, query)
        items: Sequence[Product] = self.session.execute(statement).scalars().all()
        return build_page(list(items), total, query)

    def create(
        self,
        *,
        name: str,
        description: str | None,
        price: Decimal,
        category_id: int,
        stock: int,
        low_stock_threshold: int,
        is_active: bool,
    ) -> Product:
        """Persist a new product and return it."""
        product = Product(
            name=name,
            description=description,
            price=price,
            category_id=category_id,
            stock=stock,
            low_stock_threshold=low_stock_threshold,
            is_active=is_active,
        )
        self.session.add(product)
        self.session.flush()
        return product

    def update(self, product: Product, **fields: object) -> Product:
        """Apply partial updates to a product."""
        for key, value in fields.items():
            if value is not None:
                setattr(product, key, value)
        self.session.flush()
        return product

    def delete(self, product: Product) -> None:
        """Remove a product from the database."""
        self.session.execute(delete(Product).where(Product.id == product.id))
        self.session.flush()

    def add_stock(self, product: Product, quantity: int) -> Product:
        """Increase the stock by the given quantity."""
        product.stock += quantity
        self.session.flush()
        return product

    def decrease_stock(self, product: Product, quantity: int) -> Product:
        """Decrease the stock by the given quantity."""
        product.stock -= quantity
        self.session.flush()
        return product

    def category_exists(self, category_id: int) -> bool:
        """Return True if the category exists and is persisted."""
        return self.session.get(Category, category_id) is not None
