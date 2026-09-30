"""Unit of work: one session shared by every repository of a request."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.repositories.category_repository import CategoryRepository
from app.repositories.customer_repository import CustomerRepository
from app.repositories.order_repository import OrderRepository
from app.repositories.product_repository import ProductRepository
from app.repositories.table_repository import TableRepository
from app.repositories.user_repository import UserRepository


class UnitOfWork:
    """Expose every repository plus the transaction control of a session.

    Repositories only ``flush``; services call :meth:`commit` once they are done,
    which keeps multi-step operations (an order with its lines, for instance)
    atomic.
    """

    def __init__(self, session: Session) -> None:
        """Bind every repository to the given session."""
        self.session = session
        self.categories = CategoryRepository(session)
        self.customers = CustomerRepository(session)
        self.orders = OrderRepository(session)
        self.products = ProductRepository(session)
        self.tables = TableRepository(session)
        self.users = UserRepository(session)

    def commit(self) -> None:
        """Persist the pending changes."""
        self.session.commit()

    def rollback(self) -> None:
        """Discard the pending changes."""
        self.session.rollback()

    def flush(self) -> None:
        """Send the pending changes to the database without committing."""
        self.session.flush()
