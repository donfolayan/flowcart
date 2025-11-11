import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class OrderStatusEnum(enum.StrEnum):
    pending = "pending"
    awaiting_payment = "awaiting_payment"
    authorized = "authorized"
    paid = "paid"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
    refunded = "refunded"


order_status = PGEnum(*(e.value for e in OrderStatusEnum), name="order_status_enum")
