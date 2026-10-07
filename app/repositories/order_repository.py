from collections.abc import Iterable

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderItem, OrderStatus
from app.repositories.base import PaginatedResult, paginate
from app.schemas.common import Pagination

RELATIONS = (
    selectinload(Order.items).selectinload(OrderItem.product),
    selectinload(Order.table),
    selectinload(Order.waiter),
    selectinload(Order.payment),
)


class OrderRepository:
    """Acceso a datos de pedidos."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión de base de datos."""
        self.session = session

    def _with_relations(self, statement: Select[Order]) -> Select[Order]:
        """Carga eagerly las relaciones del pedido para evitar N+1."""
        return statement.options(*RELATIONS)

    def get(self, order_id: int) -> Order | None:
        """Devuelve un pedido con sus relaciones, o `None` si no existe."""
        return self.session.execute(
            self._with_relations(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()

    def _base_query(
        self,
        *,
        status: OrderStatus | None = None,
        table_id: int | None = None,
        waiter_id: int | None = None,
    ) -> Select[Order]:
        statement = select(Order)
        if status is not None:
            statement = statement.where(Order.status == status)
        if table_id is not None:
            statement = statement.where(Order.table_id == table_id)
        if waiter_id is not None:
            statement = statement.where(Order.waiter_id == waiter_id)
        return statement

    def list(
        self,
        pagination: Pagination,
        *,
        status: OrderStatus | None = None,
        table_id: int | None = None,
        waiter_id: int | None = None,
    ) -> PaginatedResult[Order]:
        """Devuelve una página de pedidos filtrada."""
        statement = self._base_query(
            status=status, table_id=table_id, waiter_id=waiter_id
        ).order_by(Order.id.desc())
        return paginate(self.session, self._with_relations(statement), pagination)

    def list_by_statuses(
        self, pagination: Pagination, statuses: Iterable[OrderStatus]
    ) -> PaginatedResult[Order]:
        """Devuelve una página de pedidos cuyo estado está en la colección dada."""
        statement = self._base_query().where(Order.status.in_(list(statuses)))
        statement = statement.order_by(Order.id.asc())
        return paginate(self.session, self._with_relations(statement), pagination)

    def add_item(
        self,
        order: Order,
        *,
        product_id: int,
        quantity: int,
        unit_price: float,
    ) -> OrderItem:
        """Añade una línea a un pedido y devuelve la línea creada."""
        item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            quantity=quantity,
            unit_price=unit_price,
            subtotal=round(unit_price * quantity, 2),
        )
        self.session.add(item)
        self.session.flush()
        return item

    def get_by_tracking_code(self, code: str) -> Order | None:
        """Devuelve un pedido por su código de seguimiento público."""
        return self.session.execute(
            self._with_relations(select(Order).where(Order.tracking_code == code))
        ).scalar_one_or_none()

    def create(
        self,
        *,
        table_id: int | None,
        waiter_id: int | None,
        order_type: str | None = None,
        customer_name: str | None = None,
        notes: str | None = None,
        tracking_code: str | None = None,
    ) -> Order:
        """Persiste un nuevo pedido vacío y lo devuelve."""
        order = Order(
            table_id=table_id,
            waiter_id=waiter_id,
            total_amount=0.0,
            order_type=order_type,
            customer_name=customer_name,
            notes=notes,
            tracking_code=tracking_code,
        )
        self.session.add(order)
        self.session.flush()
        return order

    def recalculate_total(self, order: Order) -> float:
        """Recalcula el total del pedido a partir de sus líneas."""
        total = round(sum(item.subtotal for item in order.items), 2)
        order.total_amount = total
        self.session.flush()
        return total

    def remove_item(self, item: OrderItem) -> None:
        """Elimina una línea del pedido."""
        self.session.delete(item)
        self.session.flush()

    def update_status(self, order: Order, status: OrderStatus) -> Order:
        """Cambia el estado del pedido."""
        order.status = status
        self.session.flush()
        return order

    def delete(self, order: Order) -> None:
        """Elimina un pedido de la base de datos."""
        self.session.delete(order)
        self.session.flush()
