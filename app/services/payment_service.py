from typing import ClassVar

from sqlalchemy.orm import Session

from app.core.exceptions import BadRequestException, NotFoundException
from app.models import Order, OrderStatus, Payment
from app.repositories.order_repository import OrderRepository
from app.repositories.payment_repository import PaymentRepository
from app.schemas.order import PaymentCreate


class PaymentService:
    """Lógica de negocio de pagos.

    Cada pedido admite un único pago: la columna `payments.order_id` es única.
    """

    #: Estados en los que se admite cobrar.
    PAYABLE_STATUSES: ClassVar[frozenset[OrderStatus]] = frozenset(
        {OrderStatus.DELIVERED}
    )

    #: Tolerancia al comparar el importe pagado con el total del pedido.
    AMOUNT_TOLERANCE = 0.01

    def __init__(self, session: Session) -> None:
        """Guarda la sesión y los repositorios necesarios."""
        self.session = session
        self.payments = PaymentRepository(session)
        self.orders = OrderRepository(session)

    def _get_order(self, order_id: int) -> Order:
        """Devuelve el pedido a cobrar o lanza `NotFoundException`."""
        order = self.orders.get(order_id)
        if order is None:
            raise NotFoundException("Pedido no encontrado")
        return order

    def pay_order(self, order_id: int, data: PaymentCreate) -> Payment:
        """Registra el pago de un pedido entregado y no pagado."""
        order = self._get_order(order_id)

        if self.payments.order_is_paid(order_id):
            raise BadRequestException("El pedido ya está pagado")

        if order.status not in self.PAYABLE_STATUSES:
            raise BadRequestException(
                f"No se puede cobrar un pedido en estado {order.status.value}"
            )

        if not order.items:
            raise BadRequestException("No se puede cobrar un pedido sin productos")

        if abs(data.amount - order.total_amount) > self.AMOUNT_TOLERANCE:
            raise BadRequestException(
                f"El importe debe coincidir con el total del pedido ({order.total_amount:.2f})"
            )

        payment = self.payments.create(
            order_id=order_id, amount=data.amount, method=data.method
        )
        self.session.commit()
        return payment

    def get_by_order(self, order_id: int) -> Payment:
        """Devuelve el pago de un pedido o lanza `NotFoundException`."""
        self._get_order(order_id)
        payment = self.payments.get_by_order(order_id)
        if payment is None:
            raise NotFoundException("El pedido todavía no está pagado")
        return payment

    def cancel_payment(self, order_id: int) -> None:
        """Anula el pago de un pedido para poder cobrarlo de nuevo."""
        payment = self.get_by_order(order_id)
        self.payments.delete(payment)
        self.session.commit()
