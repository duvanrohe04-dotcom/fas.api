"""Product service layer with business rules."""

from __future__ import annotations

import logging
from decimal import Decimal

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Product
from app.repositories import ListQuery, UnitOfWork
from app.schemas.common import Page

logger = logging.getLogger(__name__)


class ProductService:
    """Orchestrate product operations enforcing business rules."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Store the unit of work used for data access and transactions."""
        self.uow = uow
        self.repository = uow.products

    def get(self, product_id: int) -> Product:
        """Return a product or raise a 404."""
        product = self.repository.get(product_id)
        if product is None:
            raise NotFoundError(f"Producto {product_id} no encontrado")
        return product

    def list(
        self,
        query: ListQuery,
        *,
        category_id: int | None = None,
        is_active: bool | None = None,
        low_stock: bool | None = None,
    ) -> Page[Product]:
        """Return a paginated list of products."""
        return self.repository.list(
            query,
            category_id=category_id,
            is_active=is_active,
            low_stock=low_stock,
        )

    def create(
        self,
        *,
        name: str,
        description: str | None,
        price: Decimal,
        category_id: int,
        stock: int = 0,
        low_stock_threshold: int = 5,
        is_active: bool = True,
    ) -> Product:
        """Create a new product verifying its category exists."""
        if not self.repository.category_exists(category_id):
            raise NotFoundError(f"Categoría {category_id} no encontrada")
        product = self.repository.create(
            name=" ".join(name.split()),
            description=description,
            price=price,
            category_id=category_id,
            stock=stock,
            low_stock_threshold=low_stock_threshold,
            is_active=is_active,
        )
        self.uow.commit()
        logger.info(
            "Product created",
            extra={"product_id": product.id, "product_name": product.name},
        )
        return product

    def update(
        self,
        product_id: int,
        *,
        name: str | None = None,
        description: str | None = None,
        price: Decimal | None = None,
        category_id: int | None = None,
        stock: int | None = None,
        low_stock_threshold: int | None = None,
        is_active: bool | None = None,
    ) -> Product:
        """Update a product enforcing domain constraints."""
        product = self.get(product_id)
        if category_id is not None and not self.repository.category_exists(category_id):
            raise NotFoundError(f"Categoría {category_id} no encontrada")
        if price is not None and price < 0:
            raise BusinessRuleError("El precio no puede ser negativo")
        if stock is not None and stock < 0:
            raise ConflictError("El stock no puede ser negativo")
        if low_stock_threshold is not None and low_stock_threshold < 0:
            raise BusinessRuleError("El umbral de stock bajo no puede ser negativo")
        fields: dict[str, object] = {
            "description": description,
            "price": price,
            "category_id": category_id,
            "stock": stock,
            "low_stock_threshold": low_stock_threshold,
            "is_active": is_active,
        }
        if name is not None:
            fields["name"] = " ".join(name.split())
        self.repository.update(product, **fields)
        self.uow.commit()
        logger.info("Product updated", extra={"product_id": product.id, "fields": list(fields)})
        return product

    def delete(self, product_id: int) -> int:
        """Delete a product by id."""
        product = self.get(product_id)
        self.repository.delete(product)
        self.uow.commit()
        logger.info("Product deleted", extra={"product_id": product_id})
        return product_id

    def adjust_stock(self, product_id: int, *, quantity: int, reason: str | None = None) -> Product:
        """Increase the stock of a product after a purchase or restock."""
        if quantity <= 0:
            raise BusinessRuleError("La cantidad debe ser mayor que cero")
        product = self.get(product_id)
        product = self.repository.add_stock(product, quantity)
        self.uow.commit()
        logger.info(
            "Product stock increased",
            extra={
                "product_id": product_id,
                "quantity": quantity,
                "reason": reason,
                "stock": product.stock,
            },
        )
        return product
