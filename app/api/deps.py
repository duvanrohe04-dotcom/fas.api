"""Reusable FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import Depends, Query
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.repositories import ListQuery, UnitOfWork
from app.services import (
    CategoryService,
    CustomerService,
    OrderService,
    ProductService,
    TableService,
)

DbSession = Annotated[Session, Depends(get_db)]


def get_unit_of_work(session: DbSession) -> UnitOfWork:
    """Provide a unit of work bound to the request session."""
    return UnitOfWork(session)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def pagination_params(
    page: Annotated[int, Query(ge=1, description="Página solicitada (desde 1).")] = 1,
    size: Annotated[int, Query(ge=1, le=100, description="Elementos por página (máx. 100).")] = 20,
    search: Annotated[
        str | None,
        Query(max_length=120, description="Búsqueda parcial por nombre."),
    ] = None,
    sort_by: Annotated[str, Query(description="Campo por el que se ordena el listado.")] = "id",
    sort_dir: Annotated[
        Literal["asc", "desc"],
        Query(description="Sentido del ordenamiento."),
    ] = "asc",
) -> ListQuery:
    """Build a normalised list query from the query string."""
    settings = get_settings()
    return ListQuery(
        page=page,
        size=min(size, settings.MAX_PAGE_SIZE),
        search=search,
        sort_by=sort_by,
        sort_dir=sort_dir,
    )


PaginationParams = Annotated[ListQuery, Depends(pagination_params)]


def get_category_service(uow: UnitOfWorkDep) -> CategoryService:
    """Provide a category service bound to the request unit of work."""
    return CategoryService(uow)


def get_product_service(uow: UnitOfWorkDep) -> ProductService:
    """Provide a product service bound to the request unit of work."""
    return ProductService(uow)


def get_customer_service(uow: UnitOfWorkDep) -> CustomerService:
    """Provide a customer service bound to the request unit of work."""
    return CustomerService(uow)


def get_table_service(uow: UnitOfWorkDep) -> TableService:
    """Provide a table service bound to the request unit of work."""
    return TableService(uow)


def get_order_service(uow: UnitOfWorkDep) -> OrderService:
    """Provide an order service bound to the request unit of work."""
    return OrderService(uow)


CategoryServiceDep = Annotated[CategoryService, Depends(get_category_service)]
ProductServiceDep = Annotated[ProductService, Depends(get_product_service)]
CustomerServiceDep = Annotated[CustomerService, Depends(get_customer_service)]
TableServiceDep = Annotated[TableService, Depends(get_table_service)]
OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
