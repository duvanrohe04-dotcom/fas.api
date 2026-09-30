"""Category service layer with business rules."""

from __future__ import annotations

import logging

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.core.utils import to_slug
from app.models import Category
from app.repositories import ListQuery, UnitOfWork
from app.schemas.common import Page

logger = logging.getLogger(__name__)


class CategoryService:
    """Orchestrate category operations enforcing business rules."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Store the unit of work used for data access and transactions."""
        self.uow = uow
        self.repository = uow.categories

    def get(self, category_id: int) -> Category:
        """Return a category or raise a 404."""
        category = self.repository.get(category_id)
        if category is None:
            raise NotFoundError(f"Categoría {category_id} no encontrada")
        return category

    def list(self, query: ListQuery) -> Page[Category]:
        """Return a paginated list of categories."""
        return self.repository.list(query)

    def get_by_slug(self, slug: str) -> Category:
        """Return a category identified by its slug or raise a 404."""
        category = self.repository.get_by_slug(slug)
        if category is None:
            raise NotFoundError(f"No existe una categoría con el slug '{slug}'")
        return category

    def product_count(self, category_id: int) -> int:
        """Return how many products belong to the given category."""
        return self.repository.count_products(category_id)

    def create(
        self,
        *,
        name: str,
        description: str | None = None,
        is_active: bool = True,
    ) -> Category:
        """Create a new category ensuring its name is unique."""
        normalized = " ".join(name.split())
        if self.repository.get_by_name(normalized):
            raise ConflictError(f"La categoría '{normalized}' ya existe")
        slug = to_slug(normalized)
        existing_slug = self.repository.get_by_slug(slug)
        if existing_slug:
            slug = f"{slug}-{existing_slug.id + 1}"
        category = self.repository.create(
            name=normalized,
            slug=slug,
            description=description,
            is_active=is_active,
        )
        self.uow.commit()
        logger.info(
            "Category created",
            extra={"category_id": category.id, "category_name": category.name},
        )
        return category

    def update(
        self,
        category_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        is_active: bool | None = None,
    ) -> Category:
        """Update an existing category enforcing uniqueness."""
        category = self.get(category_id)
        fields: dict[str, object] = {
            "description": description,
            "is_active": is_active,
        }
        if name:
            normalized = " ".join(name.split())
            existing = self.repository.get_by_name(normalized)
            if existing and existing.id != category.id:
                raise ConflictError(f"La categoría '{normalized}' ya existe")
            fields["name"] = normalized
            fields["slug"] = to_slug(normalized)
        self.repository.update(category, **fields)
        self.uow.commit()
        logger.info("Category updated", extra={"category_id": category.id, "fields": list(fields)})
        return category

    def delete(self, category_id: int) -> int:
        """Delete a category unless it still contains products."""
        category = self.get(category_id)
        product_count = self.repository.count_products(category_id)
        if product_count > 0:
            raise BusinessRuleError(
                f"No se puede eliminar la categoría porque tiene {product_count} productos",
                details={"product_count": product_count},
            )
        self.repository.delete(category)
        self.uow.commit()
        logger.info("Category deleted", extra={"category_id": category_id})
        return category_id
