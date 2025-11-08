import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class CartStatus(enum.StrEnum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"
    cancelled = "cancelled"
    expired = "expired"
    archived = "archived"


cart_status = PGEnum(*(e.value for e in CartStatus), name="cart_status")
