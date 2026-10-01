from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Payment, PaymentMethod


class PaymentRepository:
    """Acceso a datos de pagos."""

    def __init__(self, session: Session) -> None:
        """Guarda la sesión de base de datos."""
        self.session = session

    def get(self, payment_id: int) -> Payment | None:
        """Devuelve un pago por su id, o `None` si no existe."""
        return self.session.execute(
            select(Payment).where(Payment.id == payment_id)
        ).scalar_one_or_none()

    def get_by_order(self, order_id: int) -> Payment | None:
        """Devuelve el pago de un pedido, o `None` si todavía no está pagado."""
        return self.session.execute(
            select(Payment).where(Payment.order_id == order_id)
        ).scalar_one_or_none()

    def order_is_paid(self, order_id: int) -> bool:
        """Indica si el pedido ya tiene un pago registrado."""
        return (
            self.session.execute(
                select(func.count())
                .select_from(Payment)
                .where(Payment.order_id == order_id)
            ).scalar_one()
            > 0
        )

    def create(self, *, order_id: int, amount: float, method: PaymentMethod) -> Payment:
        """Persiste un nuevo pago y lo devuelve."""
        payment = Payment(order_id=order_id, amount=amount, method=method)
        self.session.add(payment)
        self.session.flush()
        return payment

    def delete(self, payment: Payment) -> None:
        """Elimina un pago de la base de datos."""
        self.session.delete(payment)
        self.session.flush()
