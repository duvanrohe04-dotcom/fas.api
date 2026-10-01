from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, DbSession
from app.schemas.common import Page, PaginationDep
from app.schemas.order import OrderRead
from app.services.order_service import OrderService

router = APIRouter(prefix="/kitchen", tags=["Kitchen"])


def get_order_service(session: DbSession) -> OrderService:
    """Devuelve el servicio de pedidos ligado a la sesión de la petición."""
    return OrderService(session)


OrderServiceDep = Annotated[OrderService, Depends(get_order_service)]


@router.get(
    "/orders",
    response_model=Page[OrderRead],
    summary="Pedidos activos de cocina",
)
def list_kitchen_orders(
    pagination: PaginationDep, service: OrderServiceDep, _: CurrentUser
) -> Page[OrderRead]:
    """
    Devuelve los pedidos pendientes y en preparación, del más antiguo al más reciente.
    """
    return service.list_kitchen(pagination)
