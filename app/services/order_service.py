"""Order service layer: creation, stock reservation and status transitions."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from app.core.dates import ZERO, quantize_money, utcnow
from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    InsufficientStockError,
    NotFoundError,
)
from app.models import Customer, Order, OrderStatus, Product, Table, User
from app.repositories import ListQuery, UnitOfWork
from app.schemas.common import Page
from app.schemas.order import OrderItemCreate

logger = logging.getLogger(__name__)


class OrderService:
    """Orchestrate order operations enforcing the cafe business rules."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Store the unit of work used for data access and transactions."""
        self.uow = uow
        self.repository = uow.orders
        self.products = uow.products
        self.customers = uow.customers
        self.tables = uow.tables

    def get(self, order_id: int) -> Order:
        """Return an order or raise a 404."""
        order = self.repository.get(order_id)
        if order is None:
            raise NotFoundError(f"Pedido {order_id} no encontrado")
        return order

    def get_by_code(self, code: str) -> Order:
        """Return an order by its public code or raise a 404."""
        order = self.repository.get_by_code(code)
        if order is None:
            raise NotFoundError(f"Pedido {code} no encontrado")
        return order

    def list(
        self,
        query: ListQuery,
        *,
        status: OrderStatus | None = None,
        table_id: int | None = None,
        customer_id: int | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Page[Order]:
        """Return a paginated list of orders filtered by the given criteria."""
        return self.repository.list(
            query,
            status=status,
            table_id=table_id,
            customer_id=customer_id,
            user_id=user_id,
            date_from=date_from,
            date_to=date_to,
        )

    def kitchen_board(self) -> list[Order]:
        """Return the orders the kitchen has to prepare or serve."""
        return self.repository.kitchen_board()

    def create(
        self,
        *,
        items: Sequence[OrderItemCreate],
        user: User,
        customer_id: int | None = None,
        table_id: int | None = None,
        discount: Decimal = ZERO,
        tax: Decimal = ZERO,
        notes: str | None = None,
    ) -> Order:
        """Create an order computing prices server side and reserving stock."""
        customer = self._resolve_customer(customer_id)
        table = self._resolve_table(table_id)
        lines = self._build_lines(items)

        subtotal = quantize_money(sum((line["subtotal"] for line in lines), start=ZERO))
        discount = quantize_money(discount)
        tax = quantize_money(tax)
        if discount > subtotal:
            raise BusinessRuleError(
                "El descuento no puede ser mayor que el subtotal",
                details={"subtotal": f"{subtotal:.2f}", "discount": f"{discount:.2f}"},
            )
        total = quantize_money(subtotal - discount + tax)

        order = self.repository.create(
            user_id=user.id,
            customer_id=customer.id if customer else None,
            table_id=table.id if table else None,
            discount=discount,
            tax=tax,
            notes=notes,
        )
        order.subtotal = subtotal
        order.total = total
        for line in lines:
            self.repository.add_item(
                order,
                product_id=line["product_id"],
                product_name=line["product_name"],
                unit_price=line["unit_price"],
                quantity=line["quantity"],
                subtotal=line["subtotal"],
                notes=line["notes"],
            )
            self.products.decrease_stock(line["product"], line["quantity"])
        self.uow.commit()
        logger.info(
            "Order created",
            extra={
                "order_id": order.id,
                "order_code": order.code,
                "total": str(total),
                "lines": len(lines),
                "user_id": user.id,
            },
        )
        return self.get(order.id)

    def change_status(
        self,
        order_id: int,
        new_status: OrderStatus,
        *,
        reason: str | None = None,
    ) -> Order:
        """Move an order to another status honouring the allowed transitions."""
        order = self.get(order_id)
        previous_status = order.status
        if new_status == previous_status:
            raise BusinessRuleError(
                f"El pedido ya está en estado {previous_status.value}",
                details={"status": previous_status.value},
            )
        if not order.can_transition_to(new_status):
            raise BusinessRuleError(
                f"No se puede pasar de {previous_status.value} a {new_status.value}",
                details={
                    "current_status": previous_status.value,
                    "requested_status": new_status.value,
                    "allowed_statuses": [status.value for status in order.next_statuses()],
                },
            )
        if new_status is OrderStatus.CANCELLED:
            self._validate_cancellation(order, reason)
            self._restore_stock(order)
            self.repository.update(
                order,
                status=new_status,
                cancelled_reason=reason.strip() if reason else None,
                delivered_at=None,
            )
        elif new_status is OrderStatus.DELIVERED:
            self.repository.update(order, status=new_status, delivered_at=utcnow())
        else:
            self.repository.update(order, status=new_status)
        self.uow.commit()
        logger.info(
            "Order status changed",
            extra={
                "order_id": order.id,
                "order_code": order.code,
                "previous_status": previous_status.value,
                "new_status": new_status.value,
            },
        )
        return self.get(order.id)

    def cancel(self, order_id: int, *, reason: str) -> Order:
        """Cancel an order and give the reserved stock back."""
        return self.change_status(order_id, OrderStatus.CANCELLED, reason=reason)

    def _validate_cancellation(self, order: Order, reason: str | None) -> None:
        """Ensure the order can be cancelled."""
        if not reason or not reason.strip():
            raise BusinessRuleError("Debes indicar el motivo de la cancelación")
        if order.paid_amount > ZERO:
            raise ConflictError(
                "El pedido tiene pagos registrados y no puede cancelarse sin reembolso"
            )

    def _resolve_customer(self, customer_id: int | None) -> Customer | None:
        """Return the customer of the order when the id is provided."""
        if customer_id is None:
            return None
        customer = self.customers.get(customer_id)
        if customer is None:
            raise NotFoundError(f"Cliente {customer_id} no encontrado")
        if not customer.is_active:
            raise BusinessRuleError(f"El cliente {customer_id} está inactivo")
        return customer

    def _resolve_table(self, table_id: int | None) -> Table | None:
        """Return the table of the order when the id is provided."""
        if table_id is None:
            return None
        table = self.tables.get(table_id)
        if table is None:
            raise NotFoundError(f"Mesa {table_id} no encontrada")
        if not table.is_active:
            raise BusinessRuleError(f"La mesa {table_id} está inactiva")
        open_order = self.repository.open_for_table(table.id)
        if open_order is not None:
            raise ConflictError(
                f"La mesa {table.number} ya tiene el pedido {open_order.code} abierto",
                details={"order_id": open_order.id, "order_code": open_order.code},
            )
        return table

    def _build_lines(self, items: Sequence[OrderItemCreate]) -> list[dict[str, object]]:
        """Validate the requested lines and compute their subtotals."""
        quantities: dict[int, int] = {}
        notes_by_product: dict[int, str | None] = {}
        for item in items:
            quantities[item.product_id] = quantities.get(item.product_id, 0) + item.quantity
            notes_by_product.setdefault(item.product_id, item.notes)

        lines: list[dict[str, object]] = []
        for product_id, quantity in quantities.items():
            product: Product | None = self.products.get(product_id)
            if product is None:
                raise NotFoundError(f"Producto {product_id} no encontrado")
            if not product.is_active:
                raise BusinessRuleError(f"El producto {product.name} no está disponible")
            if quantity > product.stock:
                raise InsufficientStockError(
                    f"Stock insuficiente de {product.name}",
                    details={
                        "product_id": product.id,
                        "product_name": product.name,
                        "requested": quantity,
                        "available": product.stock,
                    },
                )
            unit_price = quantize_money(product.price)
            lines.append(
                {
                    "product": product,
                    "product_id": product.id,
                    "product_name": product.name,
                    "unit_price": unit_price,
                    "quantity": quantity,
                    "subtotal": quantize_money(unit_price * quantity),
                    "notes": notes_by_product.get(product_id),
                }
            )
        return lines

    def _restore_stock(self, order: Order) -> None:
        """Return the units reserved by a cancelled order to the catalogue."""
        for item in order.items:
            product = self.products.get(item.product_id)
            if product is not None:
                self.products.add_stock(product, item.quantity)
