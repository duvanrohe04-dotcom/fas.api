"""Table data access layer."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Table
from app.repositories.base import (
    ListQuery,
    apply_pagination,
    apply_search,
    build_page,
    count_statement,
)
from app.schemas.common import Page


class TableRepository:
    """CRUD and listing operations for dining tables."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def get(self, table_id: int) -> Table | None:
        """Fetch a table by primary key."""
        return self.session.get(Table, table_id)

    def get_by_number(self, number: int) -> Table | None:
        """Fetch a table by its number."""
        return self.session.execute(
            select(Table).where(Table.number == number)
        ).scalar_one_or_none()

    def list(
        self,
        query: ListQuery,
        *,
        is_active: bool | None = None,
        is_occupied: bool | None = None,
    ) -> Page[Table]:
        """Return a paginated list of tables marking the occupied ones."""
        from app.models import Order
        from app.models.order import ACTIVE_TABLE_STATUSES

        statement = select(Table)
        if is_active is not None:
            statement = statement.where(Table.is_active.is_(is_active))
        occupied_ids = set(
            self.session.execute(
                select(Order.table_id).where(
                    Order.table_id.is_not(None),
                    Order.status.in_(ACTIVE_TABLE_STATUSES),
                )
            ).scalars()
        )
        if is_occupied is True:
            statement = statement.where(Table.id.in_(occupied_ids or {-1}))
        elif is_occupied is False:
            statement = statement.where(Table.id.notin_(occupied_ids or {-1}))
        statement = apply_search(statement, query, Table.name)
        total = self.session.execute(count_statement(statement)).scalar_one()
        statement = apply_pagination(statement, query)
        items: Sequence[Table] = self.session.execute(statement).scalars().all()
        for table in items:
            table.is_occupied = table.id in occupied_ids  # type: ignore[attr-defined]
        return build_page(list(items), total, query)

    def create(self, *, number: int, name: str, capacity: int, is_active: bool) -> Table:
        """Persist a new table and return it."""
        table = Table(number=number, name=name, capacity=capacity, is_active=is_active)
        self.session.add(table)
        self.session.flush()
        return table

    def update(self, table: Table, **fields: object) -> Table:
        """Apply partial updates to a table."""
        for key, value in fields.items():
            if value is not None:
                setattr(table, key, value)
        self.session.flush()
        return table

    def delete(self, table: Table) -> None:
        """Remove a table from the database."""
        self.session.delete(table)
        self.session.flush()
