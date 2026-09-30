"""Order endpoints: creation, listing and status transitions."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated

from fastapi import APIRouter, Path, Query, status

from app.api.auth_deps import CashierUser, StaffUser
from app.api.deps import OrderServiceDep, PaginationParams
from app.models import OrderStatus
from app.schemas.common import ErrorResponse, Page
from app.schemas.order import (
    OrderCancel,
    OrderCreate,
    OrderRead,
    OrderStatusUpdate,
    OrderSummaryRead,
)

router = APIRouter(prefix="/orders", tags=["orders"])

FORBIDDEN = {403: {"model": ErrorResponse, "description": "Rol sin permisos"}}
NOT_FOUND = {404: {"model": ErrorResponse, "description": "El pedido no existe"}}
VALIDATION = {422: {"model": ErrorResponse, "description": "Datos inválidos"}}
CONFLICT = {409: {"model": ErrorResponse, "description": "Conflicto con el estado actual"}}


def _start_of_day(day: date | None) -> datetime | None:
    """Lower bound of a date filter expressed in UTC."""
    return None if day is None else datetime.combine(day, time.min)


def _end_of_day(day: date | None) -> datetime | None:
    """Upper bound of a date filter expressed in UTC."""
    return None if day is None else datetime.combine(day, time.max)


@router.get(
    "",
    summary="Listar pedidos",
    description="Devuelve los pedidos con filtros por estado, mesa, cliente, usuario y fecha.",
    response_model=Page[OrderSummaryRead],
    responses={200: {"description": "Página de pedidos"}, **FORBIDDEN},
)
def list_orders(
    service: OrderServiceDep,
    current_user: StaffUser,
    pagination: PaginationParams,
    status_filter: Annotated[
        OrderStatus | None,
        Query(alias="status", description="Filtra por estado del pedido."),
    ] = None,
    table_id: Annotated[int | None, Query(ge=1, description="Filtra por mesa.")] = None,
    customer_id: Annotated[int | None, Query(ge=1, description="Filtra por cliente.")] = None,
    user_id: Annotated[
        int | None, Query(ge=1, description="Filtra por usuario que lo creó.")
    ] = None,
    date_from: Annotated[
        date | None,
        Query(description="Fecha mínima de creación (UTC)."),
    ] = None,
    date_to: Annotated[
        date | None,
        Query(description="Fecha máxima de creación (UTC)."),
    ] = None,
) -> Page[OrderSummaryRead]:
    """List orders."""
    page = service.list(
        pagination,
        status=status_filter,
        table_id=table_id,
        customer_id=customer_id,
        user_id=user_id,
        date_from=_start_of_day(date_from),
        date_to=_end_of_day(date_to),
    )
    return Page[OrderSummaryRead](
        items=[OrderSummaryRead.from_model(item) for item in page.items],
        total=page.total,
        page=page.page,
        size=page.size,
        pages=page.pages,
        has_next=page.has_next,
        has_prev=page.has_prev,
    )


@router.post(
    "",
    summary="Crear pedido",
    description=(
        "Crea un pedido calculando los precios en el servidor y descontando el stock "
        "de cada producto."
    ),
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"description": "Pedido creado"},
        **FORBIDDEN,
        **NOT_FOUND,
        **CONFLICT,
        **VALIDATION,
    },
)
def create_order(
    payload: OrderCreate,
    service: OrderServiceDep,
    current_user: StaffUser,
) -> OrderRead:
    """Create an order reserving the stock of its lines."""
    order = service.create(
        items=payload.items,
        user=current_user,
        customer_id=payload.customer_id,
        table_id=payload.table_id,
        discount=payload.discount,
        tax=payload.tax,
        notes=payload.notes,
    )
    return OrderRead.from_model(order)


@router.get(
    "/{order_id}",
    summary="Obtener pedido",
    description="Devuelve un pedido con sus líneas, totales y estados alcanzables.",
    response_model=OrderRead,
    responses={200: {"description": "Pedido encontrado"}, **FORBIDDEN, **NOT_FOUND},
)
def get_order(
    service: OrderServiceDep,
    current_user: StaffUser,
    order_id: Annotated[int, Path(ge=1, description="Identificador del pedido.")],
) -> OrderRead:
    """Return a single order."""
    return OrderRead.from_model(service.get(order_id))


@router.patch(
    "/{order_id}/status",
    summary="Cambiar estado del pedido",
    description=(
        "Aplica una transición válida: pendiente → preparando → listo → entregado, "
        "y cancelación desde pendiente o preparando."
    ),
    response_model=OrderRead,
    responses={
        200: {"description": "Estado actualizado"},
        **FORBIDDEN,
        **NOT_FOUND,
        **CONFLICT,
        **VALIDATION,
    },
)
def update_order_status(
    payload: OrderStatusUpdate,
    service: OrderServiceDep,
    current_user: StaffUser,
    order_id: Annotated[int, Path(ge=1, description="Identificador del pedido.")],
) -> OrderRead:
    """Move an order to another status."""
    order = service.change_status(order_id, payload.status, reason=payload.reason)
    return OrderRead.from_model(order)


@router.post(
    "/{order_id}/cancel",
    summary="Cancelar pedido",
    description="Cancela el pedido y devuelve al catálogo el stock reservado.",
    response_model=OrderRead,
    responses={
        200: {"description": "Pedido cancelado"},
        **FORBIDDEN,
        **NOT_FOUND,
        **CONFLICT,
        **VALIDATION,
    },
)
def cancel_order(
    payload: OrderCancel,
    service: OrderServiceDep,
    current_user: CashierUser,
    order_id: Annotated[int, Path(ge=1, description="Identificador del pedido.")],
) -> OrderRead:
    """Cancel an order returning the reserved stock."""
    order = service.cancel(order_id, reason=payload.reason)
    return OrderRead.from_model(order)
