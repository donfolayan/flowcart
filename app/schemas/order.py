from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, TYPE_CHECKING
from uuid import UUID
from datetime import datetime
from app.enums.order_enums import OrderStatusEnum
from app.enums.currency_enums import CurrencyEnum

if TYPE_CHECKING:
    from .order_item import OrderItemBase
    from .address import AddressResponse
    from .payment import PaymentResponse
    from .shipping import ShippingResponse


class OrderBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: Optional[UUID] = Field(
        None, description="Unique identifier of the user who placed the order"
    )
    currency: Optional[CurrencyEnum] = Field(
        CurrencyEnum.USD, description="Currency of the order"
    )
    status: Optional[OrderStatusEnum] = Field(
        OrderStatusEnum.PENDING, description="Status of the order"
    )
    total_cents: Optional[int] = Field(
        None, description="Total amount of the order in cents"
    )
    idempotency_key: Optional[str] = Field(
        None, description="Idempotency key provided by client for safe retries"
    )
    external_reference: Optional[str] = Field(
        None, description="External reference or integration ID"
    )
    billing_address_same_as_shipping: Optional[bool] = Field(
        None, description="Whether billing address mirrors shipping address"
    )


class OrderCreate(OrderBase):
    subtotal_cents: int = Field(
        ..., description="Subtotal amount of the order in cents"
    )
    tax_cents: int = Field(..., description="Tax amount of the order in cents")
    discount_cents: int = Field(
        ..., description="Discount amount of the order in cents"
    )


class OrderUpdate(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the order")
    status: Optional[OrderStatusEnum] = Field(None, description="Status of the order")
    total_cents: Optional[int] = Field(
        None, description="Total amount of the order in cents"
    )
    version: Optional[int] = Field(
        None, description="Expected current version for optimistic concurrency"
    )


class OrderResponse(OrderBase):
    id: UUID = Field(..., description="Unique identifier of the order")
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
    items: List["OrderItemBase"] = Field(..., description="List of items in the order")
    subtotal_cents: int = Field(
        ..., description="Subtotal amount of the order in cents"
    )
    tax_cents: int = Field(..., description="Tax amount of the order in cents")
    discount_cents: int = Field(
        ..., description="Discount amount of the order in cents"
    )
    version: int = Field(
        ..., description="Version number for optimistic concurrency control"
    )
    shipping_address: Optional["AddressResponse"] = Field(
        None, description="Shipping address details"
    )
    billing_address: Optional["AddressResponse"] = Field(
        None, description="Billing address details"
    )
    payment: Optional["PaymentResponse"] = Field(None, description="Payment details")
    shipping: Optional["ShippingResponse"] = Field(None, description="Shipping details")
