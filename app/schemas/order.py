from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from app.enums.order_enums import OrderStatusEnum
from app.enums.currency_enums import CurrencyEnum

if TYPE_CHECKING:
    from .order_item import OrderItemResponse


class OrderCreate(BaseModel):
    cart_id: UUID = Field(
        ..., description="Unique identifier of the cart to create order from"
    )
    shipping_address_id: UUID = Field(
        ..., description="Unique identifier of the shipping address"
    )
    billing_address_id: Optional[UUID] = Field(
        None, description="Unique identifier of the billing address"
    )
    billing_address_same_as_shipping: bool = Field(
        True,
        description="Flag indicating if billing address is same as shipping address",
    )
    idempotency_key: Optional[str] = Field(
        None, description="Idempotency key to prevent duplicate orders", max_length=128
    )


class OrderUpdate(BaseModel):
    version: int = Field(
        ...,
        description="Current version of the order for optimistic concurrency control",
    )
    status: Optional[OrderStatusEnum] = Field(None, description="Status of the order")


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID = Field(..., description="Unique identifier of the order")
    cart_id: Optional[UUID] = Field(
        None, description="Unique identifier of the associated cart"
    )
    user_id: Optional[UUID] = Field(
        None, description="Unique identifier of the user who placed the order"
    )

    currency: CurrencyEnum = Field(..., description="Currency of the order")
    subtotal_cents: int = Field(
        ..., description="Subtotal amount of the order in cents"
    )
    tax_cents: int = Field(..., description="Tax amount of the order in cents")
    discount_cents: int = Field(
        ..., description="Discount amount of the order in cents"
    )
    total_cents: int = Field(..., description="Total amount of the order in cents")

    shipping_address_id: Optional[UUID] = Field(
        None, description="Unique identifier of the shipping address"
    )
    billing_address_id: Optional[UUID] = Field(
        None, description="Unique identifier of the billing address"
    )
    billing_address_same_as_shipping: bool = Field(
        ...,
        description="Flag indicating if billing address is same as shipping address",
    )

    status: OrderStatusEnum = Field(..., description="Status of the order")

    created_at: datetime = Field(..., description="Creation timestamp of the order")
    updated_at: datetime = Field(..., description="Last update timestamp of the order")
    placed_at: Optional[datetime] = Field(
        None, description="Timestamp when the order was placed"
    )
    paid_at: Optional[datetime] = Field(
        None, description="Timestamp when the order was paid"
    )
    fulfilled_at: Optional[datetime] = Field(
        None, description="Timestamp when the order was fulfilled"
    )
    canceled_at: Optional[datetime] = Field(
        None, description="Timestamp when the order was canceled"
    )

    version: int = Field(
        ..., description="Version number for optimistic concurrency control"
    )

    items: List["OrderItemResponse"] = Field(
        default=[], description="List of items in the order"
    )
