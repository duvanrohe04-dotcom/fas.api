"""Table service layer with business rules."""

from __future__ import annotations

import logging

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Table
from app.repositories import ListQuery, UnitOfWork
from app.schemas.common import Page

logger = logging.getLogger(__name__)


class TableService:
    """Orchestrate table operations enforcing business rules."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Store the unit of work used for data access and transactions."""
        self.uow = uow
        self.repository = uow.tables
        self.orders = uow.orders

    def get(self, table_id: int) -> Table:
        """Return a table or raise a 404."""
        table = self.repository.get(table_id)
        if table is None:
            raise NotFoundError(f"Mesa {table_id} no encontrada")
        return table

    def list(
        self,
        query: ListQuery,
        *,
        is_active: bool | None = None,
        is_occupied: bool | None = None,
    ) -> Page[Table]:
        """Return a paginated list of tables."""
        return self.repository.list(query, is_active=is_active, is_occupied=is_occupied)

    def create(self, *, number: int, name: str, capacity: int, is_active: bool = True) -> Table:
        """Create a table ensuring its number is free."""
        if self.repository.get_by_number(number) is not None:
            raise ConflictError(f"Ya existe una mesa con el número {number}")
        table = self.repository.create(
            number=number,
            name=" ".join(name.split()),
            capacity=capacity,
            is_active=is_active,
        )
        self.uow.commit()
        logger.info("Table created", extra={"table_id": table.id, "table_number": table.number})
        return table

    def update(
        self,
        table_id: int,
        *,
        number: int | None = None,
        name: str | None = None,
        capacity: int | None = None,
        is_active: bool | None = None,
    ) -> Table:
        """Update a table partially."""
        table = self.get(table_id)
        if number is not None:
            existing = self.repository.get_by_number(number)
            if existing is not None and existing.id != table.id:
                raise ConflictError(f"Ya existe una mesa con el número {number}")
        if is_active is False:
            open_order = self.orders.open_for_table(table.id)
            if open_order is not None:
                raise BusinessRuleError("La mesa tiene un pedido abierto y no puede desactivarse")
        fields: dict[str, object] = {
            "number": number,
            "capacity": capacity,
            "is_active": is_active,
        }
        if name is not None:
            fields["name"] = " ".join(name.split())
        self.repository.update(table, **fields)
        self.uow.commit()
        logger.info("Table updated", extra={"table_id": table_id})
        return table

    def delete(self, table_id: int) -> int:
        """Delete a table that has no open order."""
        table = self.get(table_id)
        if self.orders.open_for_table(table_id) is not None:
            raise BusinessRuleError("La mesa tiene un pedido abierto y no puede eliminarse")
        self.repository.delete(table)
        self.uow.commit()
        logger.info("Table deleted", extra={"table_id": table_id})
        return table_id
