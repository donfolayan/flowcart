import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class OrderStatusEnum(enum.StrEnum):
    PENDING = "pending"
    AWAITING_PAYMENT = "awaiting_payment"
    AUTHORIZED = "authorized"
    PAID = "paid"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


order_status = PGEnum(*(e.value for e in OrderStatusEnum), name="order_status_enum")
