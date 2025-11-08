import enum
from sqlalchemy.dialects.postgresql import ENUM as PGEnum


class CurrencyEnum(str, enum.Enum):
    USD = "USD"
    NGN = "NGN"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"
    AUD = "AUD"
    CAD = "CAD"
    CHF = "CHF"
    CNY = "CNY"
    SEK = "SEK"
    NZD = "NZD"


currency_enum = PGEnum(*(e.value for e in CurrencyEnum), name="currency_enum")
