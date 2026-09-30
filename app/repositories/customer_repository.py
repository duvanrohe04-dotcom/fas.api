"""Customer data access layer."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models import Customer
from app.repositories.base import (
    ListQuery,
    apply_pagination,
    apply_search,
    build_page,
    count_statement,
)
from app.schemas.common import Page


class CustomerRepository:
    """CRUD and listing operations for customers."""

    def __init__(self, session: Session) -> None:
        """Store the database session."""
        self.session = session

    def get(self, customer_id: int) -> Customer | None:
        """Fetch a customer by primary key."""
        return self.session.get(Customer, customer_id)

    def get_by_email(self, email: str) -> Customer | None:
        """Fetch a customer by email, ignoring case."""
        return self.session.execute(
            select(Customer).where(func.lower(Customer.email) == email.strip().lower())
        ).scalar_one_or_none()

    def get_by_phone(self, phone: str) -> Customer | None:
        """Fetch a customer by phone number."""
        normalized = phone.strip()
        return self.session.execute(
            select(Customer).where(
                func.replace(Customer.phone, " ", "") == normalized.replace(" ", "")
            )
        ).scalar_one_or_none()

    def list(
        self,
        query: ListQuery,
        *,
        is_active: bool | None = None,
    ) -> Page[Customer]:
        """Return a paginated list of customers."""
        statement = select(Customer)
        if is_active is not None:
            statement = statement.where(Customer.is_active.is_(is_active))
        statement = apply_search(statement, query, Customer.name, Customer.email)
        total = self.session.execute(count_statement(statement)).scalar_one()
        statement = apply_pagination(statement, query)
        items: Sequence[Customer] = self.session.execute(statement).scalars().all()
        return build_page(list(items), total, query)

    def create(
        self,
        *,
        name: str,
        email: str | None,
        phone: str | None,
        is_active: bool,
    ) -> Customer:
        """Persist a new customer and return it."""
        customer = Customer(
            name=name,
            email=email.lower() if email else None,
            phone=phone.strip() if phone else None,
            is_active=is_active,
        )
        self.session.add(customer)
        self.session.flush()
        return customer

    def update(self, customer: Customer, **fields: object) -> Customer:
        """Apply partial updates to a customer."""
        for key, value in fields.items():
            if value is not None:
                setattr(customer, key, value)
        self.session.flush()
        return customer

    def delete(self, customer: Customer) -> None:
        """Remove a customer from the database."""
        self.session.delete(customer)
        self.session.flush()

    def has_orders(self, customer: Customer) -> bool:
        """Return True when the customer already placed orders."""
        from app.models import Order

        return (
            self.session.execute(
                select(func.count(Order.id)).where(Order.customer_id == customer.id)
            ).scalar_one()
            > 0
        )

    def find_conflict(
        self,
        *,
        email: str | None,
        phone: str | None,
        exclude_id: int | None = None,
    ) -> Customer | None:
        """Return a customer already using the given email or phone."""
        conditions = []
        if email:
            conditions.append(func.lower(Customer.email) == email.strip().lower())
        if phone:
            conditions.append(
                or_(
                    Customer.phone == phone.strip(),
                    func.replace(Customer.phone, " ", "") == phone.strip().replace(" ", ""),
                )
            )
        if not conditions:
            return None
        statement = select(Customer).where(or_(*conditions))
        if exclude_id is not None:
            statement = statement.where(Customer.id != exclude_id)
        return self.session.execute(statement).scalars().first()
