"""Category data access layer."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import delete, func, select
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


class CategoryRepository:
    """CRUD and listing operations for categories."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def get(self, category_id: int) -> Category | None:
        """Fetch a single category by primary key."""
        return self.session.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Category | None:
        """Fetch a category by its slug."""
        return self.session.execute(
            select(Category).where(Category.slug == slug)
        ).scalar_one_or_none()

    def get_by_name(self, name: str) -> Category | None:
        """Fetch a category by its normalised name."""
        return self.session.execute(
            select(Category).where(func.lower(Category.name) == name.lower())
        ).scalar_one_or_none()

    def list(self, query: ListQuery) -> Page[Category]:
        """Return a paginated list of categories."""
        statement = select(Category)
        statement = apply_search(statement, query, Category.name)
        total = self.session.execute(count_statement(statement)).scalar_one()
        statement = apply_pagination(statement, query)
        items: Sequence[Category] = self.session.execute(statement).scalars().all()
        return build_page(list(items), total, query)

    def create(self, name: str, slug: str, description: str | None, is_active: bool) -> Category:
        """Persist a new category and return it."""
        category = Category(
            name=name,
            slug=slug,
            description=description,
            is_active=is_active,
        )
        self.session.add(category)
        self.session.flush()
        return category

    def update(self, category: Category, **fields: object) -> Category:
        """Apply partial updates to the given category."""
        for key, value in fields.items():
            if value is not None:
                setattr(category, key, value)
        self.session.flush()
        return category

    def delete(self, category: Category) -> None:
        """Remove the category from the database."""
        self.session.execute(delete(Category).where(Category.id == category.id))
        self.session.flush()

    def count_products(self, category_id: int) -> int:
        """Count how many products belong to the given category."""
        return self.session.execute(
            select(func.count(Product.id)).where(Product.category_id == category_id)
        ).scalar_one()
