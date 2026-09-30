"""Order data access layer."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Order, OrderItem, OrderStatus
from app.models.order import OPEN_STATUSES
from app.repositories.base import (
    ListQuery,
    apply_pagination,
    apply_search,
    build_page,
    count_statement,
)
from app.schemas.common import Page

ORDER_SORTABLE = frozenset({"id", "code", "status", "total", "created_at", "delivered_at"})


class OrderRepository:
    """CRUD, filtering and listing operations for orders."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def _with_relations(self, statement: Select[Order]) -> Select[Order]:
        """Eager load the relations needed by the read schemas."""
        return statement.options(
            selectinload(Order.items),
            selectinload(Order.customer),
            selectinload(Order.table),
            selectinload(Order.user),
        )

    def get(self, order_id: int) -> Order | None:
        """Fetch an order with its items and relations."""
        return self.session.execute(
            self._with_relations(select(Order).where(Order.id == order_id))
        ).scalar_one_or_none()

    def get_by_code(self, code: str) -> Order | None:
        """Fetch an order by its public code."""
        return self.session.execute(
            self._with_relations(select(Order).where(Order.code == code))
        ).scalar_one_or_none()

    def list(
        self,
        query: ListQuery,
        *,
        status: OrderStatus | None = None,
        statuses: Sequence[OrderStatus] | None = None,
        table_id: int | None = None,
        customer_id: int | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Page[Order]:
        """Return a paginated list of orders with the given filters."""
        statement = select(Order)
        if status is not None:
            statement = statement.where(Order.status == status)
        if statuses is not None:
            statement = statement.where(Order.status.in_(tuple(statuses)))
        if table_id is not None:
            statement = statement.where(Order.table_id == table_id)
        if customer_id is not None:
            statement = statement.where(Order.customer_id == customer_id)
        if user_id is not None:
            statement = statement.where(Order.user_id == user_id)
        if date_from is not None:
            statement = statement.where(Order.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(Order.created_at <= date_to)
        statement = apply_search(statement, query, Order.code)
        total = self.session.execute(count_statement(statement)).scalar_one()
        statement = apply_pagination(self._with_relations(statement), query)
        items: Sequence[Order] = self.session.execute(statement).scalars().all()
        return build_page(list(items), total, query)

    def open_for_table(self, table_id: int, *, exclude_order_id: int | None = None) -> Order | None:
        """Return the open order of a table, if any."""
        statement = select(Order).where(
            Order.table_id == table_id,
            Order.status.in_(OPEN_STATUSES),
        )
        if exclude_order_id is not None:
            statement = statement.where(Order.id != exclude_order_id)
        return self.session.execute(statement).scalars().first()

    def kitchen_board(self) -> list[Order]:
        """Return the orders the kitchen still has to prepare or serve."""
        statement = (
            self._with_relations(select(Order))
            .where(Order.status.in_((OrderStatus.PREPARING, OrderStatus.READY)))
            .order_by(Order.created_at.asc(), Order.id.asc())
        )
        return list(self.session.execute(statement).scalars().all())

    def create(
        self,
        *,
        user_id: int,
        customer_id: int | None,
        table_id: int | None,
        discount: Decimal,
        tax: Decimal,
        notes: str | None,
    ) -> Order:
        """Persist the order header and assign its public code."""
        order = Order(
            code=f"PED-TMP-{uuid4().hex[:12].upper()}",
            customer_id=customer_id,
            table_id=table_id,
            user_id=user_id,
            status=OrderStatus.PENDING,
            discount=discount,
            tax=tax,
            notes=notes,
        )
        self.session.add(order)
        self.session.flush()
        order.code = f"PED-{order.id:06d}"
        self.session.flush()
        return order

    def add_item(
        self,
        order: Order,
        *,
        product_id: int,
        product_name: str,
        unit_price: Decimal,
        quantity: int,
        subtotal: Decimal,
        notes: str | None,
    ) -> OrderItem:
        """Append a line to the order."""
        item = OrderItem(
            order_id=order.id,
            product_id=product_id,
            product_name=product_name,
            unit_price=unit_price,
            quantity=quantity,
            subtotal=subtotal,
            notes=notes,
        )
        self.session.add(item)
        self.session.flush()
        return item

    def update(self, order: Order, **fields: object) -> Order:
        """Apply partial updates to an order."""
        for key, value in fields.items():
            setattr(order, key, value)
        self.session.flush()
        return order
