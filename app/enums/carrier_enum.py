import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class CarrierEnum(str, enum.Enum):
    GIGLOGISTICS = "Gig Logistics"


shipping_carrier = PGEnum(*(e.value for e in CarrierEnum), name="shipping_carrier_enum")
