from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import AdminUser, CurrentUser, DbSession, StaffUser
from app.models import OrderStatus
from app.schemas.common import Page, PaginationDep
from app.schemas.order import (
    OrderCreate,
    OrderItemsAdd,
    OrderRead,
    OrdersSummary,
    OrderStatusUpdate,
    OrderTrackRead,
    PaymentCreate,
    PaymentRead,
)
from app.services.order_service import OrderService
from app.services.payment_service import PaymentService

router = APIRouter(prefix="/orders", tags=["Orders"])


def get_order_service(session: DbSession) -> OrderService:
    """Devuelve el servicio de pedidos ligado a la sesión de la petición."""
    return OrderService(session)


def get_payment_service(session: DbSession) -> PaymentService:
    """Devuelve el servicio de pagos ligado a la sesión de la petición."""
    return PaymentService(session)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]
PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


@router.get("", response_model=Page[OrderRead], summary="Listar pedidos")
def list_orders(
    pagination: PaginationDep,
    service: OrderServiceDep,
    _: CurrentUser,
    order_status: Annotated[
        OrderStatus | None, Query(alias="status", description="Filtra por estado.")
    ] = None,
    table_id: Annotated[int | None, Query(description="Filtra por mesa.")] = None,
    waiter_id: Annotated[int | None, Query(description="Filtra por mesero.")] = None,
) -> Page[OrderRead]:
    """
    Devuelve una página de pedidos, del más reciente al más antiguo.
    """
    return service.list(
        pagination, status=order_status, table_id=table_id, waiter_id=waiter_id
    )


@router.get(
    "/summary",
    response_model=OrdersSummary,
    summary="Resumen del día (admin o cajero)",
)
def orders_summary(service: OrderServiceDep, _: StaffUser) -> OrdersSummary:
    """
    Pedidos activos, pedidos y ventas de hoy, y pedidos pendientes de cobro.
    """
    return service.summary()


@router.get(
    "/track/{code}",
    response_model=OrderTrackRead,
    summary="Seguir un pedido con su código (público)",
)
def track_order(code: str, service: OrderServiceDep) -> OrderTrackRead:
    """
    Permite al cliente consultar el estado de su pedido con el código recibido.
    """
    return OrderTrackRead.model_validate(service.track(code))


@router.get("/{order_id}", response_model=OrderRead, summary="Ver un pedido")
def get_order(order_id: int, service: OrderServiceDep, _: CurrentUser) -> OrderRead:
    """
    Devuelve un pedido con sus líneas.
    """
    return OrderRead.model_validate(service.get_or_404(order_id))


@router.post(
    "",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido",
)
def create_order(
    payload: OrderCreate, service: OrderServiceDep, current_user: CurrentUser
) -> OrderRead:
    """
    Crea un pedido, descuenta el stock y ocupa la mesa si se indica.
    """
    return OrderRead.model_validate(service.create(payload, waiter_id=current_user.id))


@router.post(
    "/public",
    response_model=OrderRead,
    status_code=status.HTTP_201_CREATED,
    summary="Crear pedido como cliente (sin sesión)",
)
def create_public_order(payload: OrderCreate, service: OrderServiceDep) -> OrderRead:
    """
    Permite a un cliente hacer un pedido desde la web sin iniciar sesión.
    """
    return OrderRead.model_validate(service.create(payload))


@router.post("/{order_id}/items", response_model=OrderRead, summary="Añadir productos")
def add_items(
    order_id: int, payload: OrderItemsAdd, service: OrderServiceDep, _: CurrentUser
) -> OrderRead:
    """
    Añade líneas a un pedido pendiente o en preparación.
    """
    return OrderRead.model_validate(service.add_items(order_id, payload.items))


@router.delete(
    "/{order_id}/items/{item_id}",
    response_model=OrderRead,
    summary="Quitar un producto del pedido",
)
def remove_item(
    order_id: int, item_id: int, service: OrderServiceDep, _: CurrentUser
) -> OrderRead:
    """
    Elimina una línea del pedido y devuelve el stock correspondiente.
    """
    return OrderRead.model_validate(service.remove_item(order_id, item_id))


@router.patch(
    "/{order_id}/status", response_model=OrderRead, summary="Cambiar estado del pedido"
)
def update_status(
    order_id: int,
    payload: OrderStatusUpdate,
    service: OrderServiceDep,
    _: CurrentUser,
) -> OrderRead:
    """
    Avanza o cancela el pedido respetando las transiciones válidas.
    """
    return OrderRead.model_validate(service.update_status(order_id, payload))


@router.post(
    "/{order_id}/pay",
    response_model=PaymentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cobrar un pedido (solo admin o cajero)",
)
def pay_order(
    order_id: int,
    payload: PaymentCreate,
    service: PaymentServiceDep,
    _: StaffUser,
) -> PaymentRead:
    """
    Registra el pago de un pedido entregado. Cada pedido admite un único pago.
    """
    return PaymentRead.model_validate(service.pay_order(order_id, payload))


@router.get(
    "/{order_id}/payment",
    response_model=PaymentRead,
    summary="Ver el pago de un pedido",
)
def get_payment(
    order_id: int, service: PaymentServiceDep, _: CurrentUser
) -> PaymentRead:
    """
    Devuelve el pago registrado de un pedido.
    """
    return PaymentRead.model_validate(service.get_by_order(order_id))


@router.delete(
    "/{order_id}/payment",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Anular el pago de un pedido (solo admin)",
)
def cancel_payment(order_id: int, service: PaymentServiceDep, _: AdminUser) -> None:
    """
    Anula el pago de un pedido para poder cobrarlo de nuevo.
    """
    service.cancel_payment(order_id)
