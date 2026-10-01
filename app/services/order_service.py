from __future__ import annotations

from typing import ClassVar

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import Order, OrderStatus, Product, Table, TableStatus
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.repositories.table_repository import TableRepository
from app.schemas.common import Page, Pagination, build_page
from app.schemas.order import (
    OrderCreate,
    OrderItemCreate,
    OrderRead,
    OrderStatusUpdate,
)


class OrderService:
    """Lógica de negocio de pedidos."""

    #: Transiciones de estado permitidas.
    TRANSITIONS: ClassVar[dict[OrderStatus, frozenset[OrderStatus]]] = {
        OrderStatus.PENDING: frozenset({OrderStatus.PREPARING, OrderStatus.CANCELLED}),
        OrderStatus.PREPARING: frozenset({OrderStatus.READY, OrderStatus.CANCELLED}),
        OrderStatus.READY: frozenset({OrderStatus.DELIVERED}),
        OrderStatus.DELIVERED: frozenset(),
        OrderStatus.CANCELLED: frozenset(),
    }

    #: Estados que aparecen en la pantalla de cocina.
    KITCHEN_STATUSES: ClassVar[tuple[OrderStatus, ...]] = (
        OrderStatus.PENDING,
        OrderStatus.PREPARING,
    )

    def __init__(self, session: Session) -> None:
        """Guarda la sesión y los repositorios necesarios."""
        self.session = session
        self.orders = OrderRepository(session)
        self.payments = PaymentRepository(session)
        self.tables = TableRepository(session)

    def get_or_404(self, order_id: int) -> Order:
        """Devuelve un pedido o lanza `NotFoundException`."""
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundException("Pedido no encontrado")
        return order

    def _get_products(self, items: list[OrderItemCreate]) -> list[tuple[Product, int]]:
        """Valida las líneas y devuelve los productos con su cantidad acumulada."""
        quantities: dict[int, int] = {}
        for item in items:
            quantities[item.product_id] = (
                quantities.get(item.product_id, 0) + item.quantity
            )

        products: list[tuple[Product, int]] = []
        for product_id, quantity in quantities.items():
            product = self.session.get(Product, product_id)
            if product is None:
                raise BadRequestException(f"El producto {product_id} no existe")
            if not product.is_active:
                raise BadRequestException(
                    f"El producto {product.name} no está disponible"
                )
            products.append((product, quantity))
        return products

    def create(self, data: OrderCreate, *, waiter_id: int | None = None) -> Order:
        """Crea un pedido con sus líneas, descontando el stock."""
        products = self._get_products(data.items)

        table: Table | None = None
        if data.table_id is not None:
            table = self.tables.get(data.table_id)
            if table is None:
                raise BadRequestException("La mesa indicada no existe")

        for product, quantity in products:
            if product.stock < quantity:
                raise BadRequestException(
                    f"Stock insuficiente de {product.name}: quedan {product.stock}"
                )

        order = self.orders.create(table_id=data.table_id, waiter_id=waiter_id)

        for product, quantity in products:
            product.stock -= quantity
            self.orders.add_item(
                order,
                product_id=product.id,
                quantity=quantity,
                unit_price=product.price,
            )

        self.orders.recalculate_total(order)

        if table is not None:
            table.status = TableStatus.OCCUPIED

        self.session.commit()
        return self.get_or_404(order.id)

    def list(
        self,
        pagination: Pagination,
        *,
        status: OrderStatus | None = None,
        table_id: int | None = None,
        waiter_id: int | None = None,
    ) -> Page[OrderRead]:
        """Devuelve una página de pedidos filtrada."""
        result = self.orders.list(
            pagination, status=status, table_id=table_id, waiter_id=waiter_id
        )
        return build_page(
            [OrderRead.model_validate(item) for item in result.items],
            result.total,
            pagination,
        )

    def list_kitchen(self, pagination: Pagination) -> Page[OrderRead]:
        """Devuelve los pedidos que aún no están listos, del más antiguo al más reciente."""
        result = self.orders.list_by_statuses(pagination, self.KITCHEN_STATUSES)
        return build_page(
            [OrderRead.model_validate(item) for item in result.items],
            result.total,
            pagination,
        )

    def add_items(self, order_id: int, items: list[OrderItemCreate]) -> Order:
        """Añade líneas a un pedido pendiente o en preparación."""
        order = self.get_or_404(order_id)

        if order.status not in (OrderStatus.PENDING, OrderStatus.PREPARING):
            raise BadRequestException(
                f"No se pueden añadir productos a un pedido en estado {order.status.value}"
            )

        products = self._get_products(items)
        for product, quantity in products:
            if product.stock < quantity:
                raise BadRequestException(
                    f"Stock insuficiente de {product.name}: quedan {product.stock}"
                )

        for product, quantity in products:
            product.stock -= quantity
            existing = next(
                (item for item in order.items if item.product_id == product.id),
                None,
            )
            if existing is None:
                self.orders.add_item(
                    order,
                    product_id=product.id,
                    quantity=quantity,
                    unit_price=product.price,
                )
            else:
                existing.quantity += quantity
                existing.subtotal = round(existing.unit_price * existing.quantity, 2)
                self.session.flush()

        self.orders.recalculate_total(order)
        self.session.commit()
        return self.get_or_404(order_id)

    def remove_item(self, order_id: int, item_id: int) -> Order:
        """Elimina una línea del pedido y devuelve el stock."""
        order = self.get_or_404(order_id)

        if order.status not in (OrderStatus.PENDING, OrderStatus.PREPARING):
            raise BadRequestException(
                f"No se pueden quitar productos de un pedido en estado {order.status.value}"
            )

        item = next((line for line in order.items if line.id == item_id), None)
        if item is None:
            raise NotFoundException("La línea del pedido no existe")

        product = self.session.get(Product, item.product_id)
        if product is not None:
            product.stock += item.quantity

        self.orders.remove_item(item)
        self.session.flush()
        self.session.refresh(order)
        self.orders.recalculate_total(order)
        self.session.commit()
        return self.get_or_404(order_id)

    def update_status(self, order_id: int, data: OrderStatusUpdate) -> Order:
        """Cambia el estado del pedido validando la transición."""
        order = self.get_or_404(order_id)

        if data.status == order.status:
            return order

        allowed = self.TRANSITIONS.get(order.status, set())
        if data.status not in allowed:
            raise BadRequestException(
                f"No se puede pasar de {order.status.value} a {data.status.value}"
            )

        if data.status == OrderStatus.CANCELLED:
            self._restore_stock(order)

        self.orders.update_status(order, data.status)
        self.session.flush()

        if data.status in (OrderStatus.DELIVERED, OrderStatus.CANCELLED):
            self._release_table(order)

        self.session.commit()
        return self.get_or_404(order_id)

    def cancel(self, order_id: int) -> Order:
        """Cancela un pedido devolviendo el stock."""
        return self.update_status(
            order_id, OrderStatusUpdate(status=OrderStatus.CANCELLED)
        )

    def _restore_stock(self, order: Order) -> None:
        """Devuelve al stock las cantidades de un pedido cancelado."""
        for item in order.items:
            product = self.session.get(Product, item.product_id)
            if product is not None:
                product.stock += item.quantity
        self.session.flush()

    def _release_table(self, order: Order) -> None:
        """Libera la mesa si el pedido ya no es el único activo."""
        if order.table_id is None:
            return
        if self.tables.count_occupied_orders(order.table_id) > 0:
            return
        table = self.tables.get(order.table_id)
        if table is not None:
            table.status = TableStatus.AVAILABLE
            self.session.flush()
