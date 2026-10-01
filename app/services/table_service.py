from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import Table, TableStatus
from app.repositories.table_repository import TableRepository
from app.schemas.common import Page, Pagination, build_page
from app.schemas.table import TableRead, TableUpdate


class TableService:
    """Lógica de negocio de mesas."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión y el repositorio de mesas."""
        self.session = session
        self.tables = TableRepository(session)

    def get_or_404(self, table_id: int) -> Table:
        """Devuelve una mesa o lanza `NotFoundException`."""
        table = self.tables.get(table_id)
        if table is None:
            raise NotFoundException("Mesa no encontrada")
        return table

    def create(self, number: int, capacity: int) -> Table:
        """Crea una mesa. Falla si el número ya existe."""
        if self.tables.number_exists(number):
            raise BadRequestException("Ya existe una mesa con ese número")

        table = self.tables.create(number=number, capacity=capacity)
        self.session.commit()
        return table

    def list(
        self,
        pagination: Pagination,
        *,
        status: TableStatus | None = None,
        min_capacity: int | None = None,
    ) -> Page[TableRead]:
        """Devuelve una página de mesas filtrada."""
        result = self.tables.list(pagination, status=status, min_capacity=min_capacity)
        return build_page(
            [TableRead.model_validate(item) for item in result.items],
            result.total,
            pagination,
        )

    def update(self, table_id: int, data: TableUpdate) -> Table:
        """Actualiza parcialmente una mesa."""
        table = self.get_or_404(table_id)

        if (
            data.status == TableStatus.AVAILABLE
            and table.status == TableStatus.OCCUPIED
            and self.tables.count_occupied_orders(table_id) > 0
        ):
            raise BadRequestException(
                "No se puede liberar una mesa con pedidos en curso"
            )

        self.tables.update(table, capacity=data.capacity, status=data.status)
        self.session.commit()
        return table

    def set_status(self, table_id: int, status: TableStatus) -> Table:
        """Cambia el estado de una mesa validando los pedidos en curso."""
        return self.update(table_id, TableUpdate(status=status))

    def delete(self, table_id: int) -> None:
        """Elimina una mesa si no tiene pedidos asociados."""
        table = self.get_or_404(table_id)

        if self.tables.count_occupied_orders(table_id) > 0:
            raise BadRequestException(
                "No se puede eliminar una mesa con pedidos en curso"
            )

        self.tables.delete(table)
        self.session.commit()
