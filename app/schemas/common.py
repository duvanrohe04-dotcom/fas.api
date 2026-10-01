from typing import Annotated, Generic, TypeVar

from fastapi import Depends, Query
from pydantic import BaseModel, Field

T = TypeVar("T")

MAX_PAGE_SIZE = 100


class Page(BaseModel, Generic[T]):
    """Envoltorio estándar para respuestas paginadas."""

    items: list[T]
    total: int
    page: int
    size: int
    pages: int
    has_next: bool
    has_prev: bool


class Pagination(BaseModel):
    """Parámetros de paginación reutilizables como dependencia de FastAPI."""

    page: int = Field(default=1, ge=1, description="Página actual (1-indexada).")
    size: int = Field(
        default=10,
        ge=1,
        le=MAX_PAGE_SIZE,
        description="Elementos por página.",
    )

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.size

    @property
    def limit(self) -> int:
        return self.size


def pagination_dependency(
    page: Annotated[int, Query(ge=1, description="Página actual (1-indexada).")] = 1,
    size: Annotated[
        int, Query(ge=1, le=MAX_PAGE_SIZE, description="Elementos por página.")
    ] = 10,
) -> Pagination:
    """Dependencia de FastAPI que construye un objeto `Pagination`."""
    return Pagination(page=page, size=size)


PaginationDep = Annotated[Pagination, Depends(pagination_dependency)]


def build_page(items: list[T], total: int, pagination: Pagination) -> Page[T]:
    """Construye la respuesta paginada a partir de items ya convertidos a schema."""
    pages = -(-total // pagination.size)
    return Page[T](
        items=list(items),
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=pages,
        has_next=pagination.page < pages,
        has_prev=pagination.page > 1,
    )
