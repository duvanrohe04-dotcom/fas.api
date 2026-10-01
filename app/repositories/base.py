from dataclasses import dataclass, field
from typing import Generic, TypeVar

from sqlalchemy import Select, func, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from app.schemas.common import Pagination

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """Resultado paginado neutral (sin pydantic) con entidades ORM.

    La capa de repositorios usa esto para no acoplar modelos ORM a schemas de
    respuesta; la conversión a `Page[Schema]` se hace en la capa de servicios.
    """

    items: list[T] = field(default_factory=list)
    total: int = 0


def apply_pagination(statement: Select[T], pagination: Pagination) -> Select[T]:
    """Aplica `LIMIT`/`OFFSET` a una consulta según la paginación solicitada."""
    return statement.limit(pagination.limit).offset(pagination.offset)


def count_statement(statement: Select[T]) -> Select[int]:
    """Construye la consulta `COUNT(*)` equivalente a un `SELECT` de entidades."""
    return select(func.count()).select_from(statement.order_by(None).subquery())


def paginate(
    session: Session,
    statement: Select[T],
    pagination: Pagination,
) -> PaginatedResult[T]:
    """Ejecuta la consulta paginada y devuelve los items junto al total de filas."""
    total = session.execute(count_statement(statement)).scalar_one()
    rows = session.execute(apply_pagination(statement, pagination)).scalars().all()
    return PaginatedResult[T](items=list(rows), total=total)


def ordering(
    statement: Select[T],
    column: InstrumentedAttribute[T],
    *,
    descending: bool = False,
) -> Select[T]:
    """Ordena una consulta por una columna de forma estable."""
    return statement.order_by(column.desc() if descending else column.asc())
