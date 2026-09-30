"""Payment data access layer."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from app.models import Payment, PaymentMethod
from app.repositories.base import (
    ListQuery,
    apply_pagination,
    count_statement,
)
from app.schemas.common import Page


class PaymentRepository:
    """CRUD and listing operations for payments."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def _with_relations(self, statement: Select[Payment]) -> Select[Payment]:
        """Eager load the order and the user of the payment."""
        return statement.options(selectinload(Payment.order), selectinload(Payment.user))

    def get(self, payment_id: int) -> Payment | None:
        """Fetch a payment with its relations."""
        return self.session.execute(
            self._with_relations(select(Payment).where(Payment.id == payment_id))
        ).scalar_one_or_none()

    def list(
        self,
        query: ListQuery,
        *,
        order_id: int | None = None,
        method: PaymentMethod | None = None,
        user_id: int | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> Page[Payment]:
        """Return a paginated list of payments filtered by the given criteria."""
        statement = select(Payment)
        if order_id is not None:
            statement = statement.where(Payment.order_id == order_id)
        if method is not None:
            statement = statement.where(Payment.method == method)
        if user_id is not None:
            statement = statement.where(Payment.user_id == user_id)
        if date_from is not None:
            statement = statement.where(Payment.created_at >= date_from)
        if date_to is not None:
            statement = statement.where(Payment.created_at <= date_to)
        total = self.session.execute(count_statement(statement)).scalar_one()
        statement = apply_pagination(self._with_relations(statement), query)
        items: Sequence[Payment] = self.session.execute(statement).scalars().all()
        return build_page(list(items), total, query)

    def list_by_order(self, order_id: int) -> list[Payment]:
        """Return every payment of an order, oldest first."""
        statement = (
            self._with_relations(select(Payment))
            .where(Payment.order_id == order_id)
            .order_by(Payment.id.asc())
        )
        return list(self.session.execute(statement).scalars().all())

    def sum_by_order(self, order_id: int) -> Decimal:
        """Return the total amount already paid for an order."""
        from sqlalchemy import func

        return self.session.execute(
            select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.order_id == order_id)
        ).scalar_one()

    def create(
        self,
        *,
        order_id: int,
        user_id: int,
        method: PaymentMethod,
        amount: Decimal,
        reference: str | None,
        notes: str | None,
    ) -> Payment:
        """Persist a new payment and return it."""
        payment = Payment(
            order_id=order_id,
            user_id=user_id,
            method=method,
            amount=amount,
            reference=reference,
            notes=notes,
        )
        self.session.add(payment)
        self.session.flush()
        return payment

    def delete(self, payment: Payment) -> None:
        """Remove a payment from the database."""
        self.session.delete(payment)
        self.session.flush()