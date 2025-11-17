import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class ShippingStatusEnum(str, enum.Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    DELIVERED = "delivered"
    DELAYED = "delayed"
    CANCELLED = "cancelled"


shipping_status = PGEnum(
    *(e.value for e in ShippingStatusEnum), name="shipping_status_enum"
)
