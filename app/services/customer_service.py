"""Customer service layer with business rules."""

from __future__ import annotations

import logging

from app.core.exceptions import BusinessRuleError, ConflictError, NotFoundError
from app.models import Customer
from app.repositories import ListQuery, UnitOfWork
from app.schemas.common import Page

logger = logging.getLogger(__name__)


class CustomerService:
    """Orchestrate customer operations enforcing business rules."""

    def __init__(self, uow: UnitOfWork) -> None:
        """Store the unit of work used for data access and transactions."""
        self.uow = uow
        self.repository = uow.customers

    def get(self, customer_id: int) -> Customer:
        """Return a customer or raise a 404."""
        customer = self.repository.get(customer_id)
        if customer is None:
            raise NotFoundError(f"Cliente {customer_id} no encontrado")
        return customer

    def list(self, query: ListQuery, *, is_active: bool | None = None) -> Page[Customer]:
        """Return a paginated list of customers."""
        return self.repository.list(query, is_active=is_active)

    def create(
        self,
        *,
        name: str,
        email: str | None,
        phone: str | None,
        is_active: bool = True,
    ) -> Customer:
        """Create a customer ensuring email and phone are free."""
        self._ensure_unique(email=email, phone=phone)
        customer = self.repository.create(
            name=" ".join(name.split()),
            email=email,
            phone=phone,
            is_active=is_active,
        )
        self.uow.commit()
        logger.info("Customer created", extra={"customer_id": customer.id})
        return customer

    def update(
        self,
        customer_id: int,
        *,
        name: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        is_active: bool | None = None,
    ) -> Customer:
        """Update a customer partially."""
        customer = self.get(customer_id)
        self._ensure_unique(email=email, phone=phone, exclude_id=customer_id)
        fields: dict[str, object] = {
            "email": email.lower() if email else None,
            "phone": phone.strip() if phone else None,
            "is_active": is_active,
        }
        if name is not None:
            fields["name"] = " ".join(name.split())
        self.repository.update(customer, **fields)
        self.uow.commit()
        logger.info("Customer updated", extra={"customer_id": customer_id})
        return customer

    def delete(self, customer_id: int) -> int:
        """Delete a customer that has no orders."""
        customer = self.get(customer_id)
        if self.repository.has_orders(customer):
            raise BusinessRuleError("El cliente tiene pedidos asociados y no puede eliminarse")
        self.repository.delete(customer)
        self.uow.commit()
        logger.info("Customer deleted", extra={"customer_id": customer_id})
        return customer_id

    def _ensure_unique(
        self,
        *,
        email: str | None,
        phone: str | None,
        exclude_id: int | None = None,
    ) -> None:
        """Raise a 409 when the email or the phone are already registered."""
        conflict = self.repository.find_conflict(email=email, phone=phone, exclude_id=exclude_id)
        if conflict is None:
            return
        if email and conflict.email and conflict.email.lower() == email.strip().lower():
            raise ConflictError(f"El email {email} ya está registrado")
        raise ConflictError(f"El teléfono {phone} ya está registrado")
