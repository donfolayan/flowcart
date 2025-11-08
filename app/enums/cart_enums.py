import enum


class CartStatus(enum.StrEnum):
    active = "active"
    completed = "completed"
    abandoned = "abandoned"
    cancelled = "cancelled"
    expired = "expired"
    archived = "archived"
