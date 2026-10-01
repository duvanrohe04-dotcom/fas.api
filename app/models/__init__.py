# Registramos Base al final para asegurar que importe todos los modelos
from app.core.database import Base as Base
from app.models.base import TimestampMixin as TimestampMixin
from app.models.category import Category as Category
from app.models.order import Order as Order
from app.models.order import OrderItem as OrderItem
from app.models.order import OrderStatus as OrderStatus
from app.models.payment import Payment as Payment
from app.models.payment import PaymentMethod as PaymentMethod
from app.models.product import Product as Product
from app.models.table import Table as Table
from app.models.table import TableStatus as TableStatus
from app.models.user import RoleEnum as RoleEnum
from app.models.user import User as User
