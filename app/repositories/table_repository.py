from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models import Order, OrderStatus, Table, TableStatus
from app.repositories.base import PaginatedResult, paginate
from app.schemas.common import Pagination


class TableRepository:
    """Acceso a datos de mesas."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión de base de datos."""
        self.session = session

    def get(self, table_id: int) -> Table | None:
        """Devuelve una mesa por su id, o `None` si no existe."""
        return self.session.execute(
            select(Table).where(Table.id == table_id)
        ).scalar_one_or_none()

    def get_by_number(self, number: int) -> Table | None:
        """Devuelve una mesa por su número, o `None` si no existe."""
        return self.session.execute(
            select(Table).where(Table.number == number)
        ).scalar_one_or_none()

    def number_exists(self, number: int, *, exclude_id: int | None = None) -> bool:
        """Indica si el número ya está en uso por otra mesa."""
        existing = self.get_by_number(number)
        return existing is not None and existing.id != exclude_id

    def _base_query(
        self, *, status: TableStatus | None = None, min_capacity: int | None = None
    ) -> Select[Table]:
        statement = select(Table)
        if status is not None:
            statement = statement.where(Table.status == status)
        if min_capacity is not None:
            statement = statement.where(Table.capacity >= min_capacity)
        return statement

    def list(
        self,
        pagination: Pagination,
        *,
        status: TableStatus | None = None,
        min_capacity: int | None = None,
    ) -> PaginatedResult[Table]:
        """Devuelve una página de mesas filtrada por estado y capacidad."""
        statement = self._base_query(status=status, min_capacity=min_capacity).order_by(
            Table.number.asc()
        )
        return paginate(self.session, statement, pagination)

    def create(self, *, number: int, capacity: int) -> Table:
        """Persiste una nueva mesa y la devuelve."""
        table = Table(number=number, capacity=capacity)
        self.session.add(table)
        self.session.flush()
        return table

    def set_status(self, table: Table, status: TableStatus) -> Table:
        """Cambia el estado de una mesa."""
        table.status = status
        self.session.flush()
        return table

    def update(self, table: Table, **changes: object) -> Table:
        """Aplica cambios parciales a una mesa."""
        for field, value in changes.items():
            if value is not None:
                setattr(table, field, value)
        self.session.flush()
        return table

    def delete(self, table: Table) -> None:
        """Elimina una mesa de la base de datos."""
        self.session.delete(table)
        self.session.flush()

    def count_occupied_orders(self, table_id: int) -> int:
        """Cuenta los pedidos no cancelados ni entregados de una mesa."""
        return self.session.execute(
            select(func.count())
            .select_from(Order)
            .where(
                Order.table_id == table_id,
                Order.status.notin_([OrderStatus.CANCELLED, OrderStatus.DELIVERED]),
            )
        ).scalar_one()
