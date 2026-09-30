"""Tests for the ORM models and the order lifecycle rules."""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Category,
    Customer,
    Order,
    OrderItem,
    OrderStatus,
    Payment,
    PaymentMethod,
    Product,
    Table,
    User,
    UserRole,
)


def _seed_order(session: Session, status: OrderStatus = OrderStatus.PENDING) -> Order:
    """Create a minimal order graph for transition tests."""
    user = User(
        username="mesero",
        email="mesero@test.com",
        full_name="Mesero Demo",
        hashed_password="x",
        role=UserRole.WAITER,
    )
    session.add(user)
    session.flush()
    order = Order(code="ORD-1", user_id=user.id, status=status)
    session.add(order)
    session.commit()
    return order


def test_product_computed_flags(db: Session) -> None:
    """is_low_stock and is_available reflect the current stock."""
    category = Category(name="Cafés", slug="cafes")
    db.add(category)
    db.flush()
    product = Product(
        name="Espresso",
        price=Decimal("2.50"),
        stock=5,
        low_stock_threshold=5,
        category_id=category.id,
    )
    db.add(product)
    db.commit()

    assert product.is_low_stock is True
    assert product.is_available is True

    product.stock = 0
    assert product.is_available is False


def test_money_keeps_two_decimals(db: Session) -> None:
    """Numeric columns round amounts to two decimal places."""
    category = Category(name="Postres", slug="postres")
    db.add(category)
    db.flush()
    product = Product(
        name="Tarta",
        price=Decimal("3.456"),
        stock=10,
        category_id=category.id,
    )
    db.add(product)
    db.commit()
    db.refresh(product)

    assert product.price == Decimal("3.46")


def test_category_delete_cascades_to_products(db: Session) -> None:
    """Removing a category removes its products."""
    category = Category(name="Panadería", slug="panaderia")
    db.add(category)
    db.flush()
    product = Product(
        name="Croissant",
        price=Decimal("1.80"),
        stock=5,
        category_id=category.id,
    )
    db.add(product)
    db.commit()

    db.delete(category)
    db.commit()

    assert db.scalars(select(Product)).all() == []


def test_order_balance_and_paid_flags(db: Session) -> None:
    """balance_due and is_paid are derived from total and paid_amount."""
    order = _seed_order(db)
    order.total = Decimal("10.00")
    order.paid_amount = Decimal("4.00")
    db.commit()

    assert order.balance_due == Decimal("6.00")
    assert order.is_paid is False

    order.paid_amount = Decimal("10.00")
    assert order.is_paid is True
    assert order.balance_due == Decimal("0.00")


def test_order_status_transitions(db: Session) -> None:
    """The happy path allows pending to preparing to ready to delivered."""
    order = _seed_order(db)

    assert order.can_transition_to(OrderStatus.PREPARING) is True
    assert order.can_transition_to(OrderStatus.DELIVERED) is False

    order.status = OrderStatus.PREPARING
    assert order.can_transition_to(OrderStatus.READY) is True
    assert order.can_transition_to(OrderStatus.CANCELLED) is True

    order.status = OrderStatus.READY
    assert order.next_statuses() == [OrderStatus.DELIVERED]

    order.status = OrderStatus.DELIVERED
    assert order.next_statuses() == []

    order.status = OrderStatus.CANCELLED
    assert order.can_transition_to(OrderStatus.PENDING) is False


def test_order_graph_relationships(db: Session) -> None:
    """Items, payments, customer and table are reachable from the order."""
    user = User(
        username="cajero",
        email="cajero@test.com",
        full_name="Cajero Demo",
        hashed_password="x",
        role=UserRole.CASHIER,
    )
    customer = Customer(name="Ana", email="ana@test.com")
    table = Table(number=1, name="Mesa 1", capacity=4)
    category = Category(name="Bebidas frías", slug="bebidas-frias")
    db.add_all([user, customer, table, category])
    db.flush()
    product = Product(
        name="Limonada",
        price=Decimal("3.00"),
        stock=10,
        category_id=category.id,
    )
    db.add(product)
    db.flush()
    order = Order(code="ORD-2", user_id=user.id, customer_id=customer.id, table_id=table.id)
    order.items.append(
        OrderItem(
            product_id=product.id,
            product_name=product.name,
            unit_price=product.price,
            quantity=2,
            subtotal=Decimal("6.00"),
        )
    )
    order.payments.append(
        Payment(user_id=user.id, method=PaymentMethod.CASH, amount=Decimal("6.00"))
    )
    db.add(order)
    db.commit()

    stored = db.get(Order, order.id)
    assert stored is not None
    assert stored.customer is not None
    assert stored.customer.name == "Ana"
    assert stored.table is not None
    assert stored.table.number == 1
    assert stored.items[0].product_name == "Limonada"
    assert stored.payments[0].method is PaymentMethod.CASH


def test_order_code_is_unique(db: Session) -> None:
    """Two orders cannot share the same code."""
    _seed_order(db)
    second_user = User(
        username="otro",
        email="otro@test.com",
        full_name="Otro",
        hashed_password="x",
        role=UserRole.ADMIN,
    )
    db.add(second_user)
    db.flush()
    db.add(Order(code="ORD-1", user_id=second_user.id))

    try:
        db.commit()
    except Exception:
        db.rollback()
    else:  # pragma: no cover - only reached if the constraint is missing
        raise AssertionError("Expected an IntegrityError for the duplicated code")
