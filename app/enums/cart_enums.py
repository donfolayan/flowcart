import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class CartStatus(enum.StrEnum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    ARCHIVED = "archived"


cart_status = PGEnum(*(e.value for e in CartStatus), name="cart_status")
