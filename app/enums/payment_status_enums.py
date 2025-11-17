import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class PaymentStatusEnum(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


payment_status = PGEnum(
    *(e.value for e in PaymentStatusEnum), name="payment_status_enum"
)
