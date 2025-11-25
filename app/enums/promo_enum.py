import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class PromoTypeEnum(str, enum.Enum):
    PERCENTAGE = "percentage"
    FIXED_AMOUNT = "fixed_amount"
    FREE_SHIPPING = "free_shipping"


promo_type = PGEnum(*(e.value for e in PromoTypeEnum), name="promo_type_enum")
