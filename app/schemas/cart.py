from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from app.enums.cart_enums import CartStatus
from app.enums.currency_enums import CurrencyEnum
from app.schemas.cart_item import CartItemResponse


class CartBase(BaseModel):
    user_id: Optional[UUID] = Field(None, description="ID of the user owning the cart")
    session_id: Optional[str] = Field(None, description="Session ID for guest carts")
    status: Optional[CartStatus] = Field(None, description="Status of the cart")
    currency: Optional[CurrencyEnum] = Field(
        CurrencyEnum.USD, description="Currency of the cart"
    )

    subtotal: Optional[Decimal] = Field(
        default_factory=lambda: Decimal("0.00"),
        description="Subtotal amount of the cart",
    )
    tax_total: Optional[Decimal] = Field(
        default_factory=lambda: Decimal("0.00"),
        description="Total tax amount of the cart",
    )
    discount_total: Optional[Decimal] = Field(
        default_factory=lambda: Decimal("0.00"),
        description="Total discount amount of the cart",
    )
    shipping_total: Optional[Decimal] = Field(
        default_factory=lambda: Decimal("0.00"),
        description="Total shipping amount of the cart",
    )

    expires_at: Optional[datetime] = Field(
        None, description="Expiration datetime for guest carts"
    )
    extra_data: Optional[dict] = Field(None, description="Additional data for the cart")
    model_config = ConfigDict(from_attributes=True)


class CartCreate(CartBase):
    pass


class CartUpdate(BaseModel):
    status: Optional[CartStatus] = Field(None, description="Status of the cart")
    subtotal: Optional[Decimal] = Field(None, description="Subtotal amount of the cart")
    tax_total: Optional[Decimal] = Field(
        None, description="Total tax amount of the cart"
    )
    discount_total: Optional[Decimal] = Field(
        None, description="Total discount amount of the cart"
    )
    shipping_total: Optional[Decimal] = Field(
        None, description="Total shipping amount of the cart"
    )

    extra_data: Optional[dict] = Field(None, description="Additional data for the cart")
    model_config = ConfigDict(from_attributes=True)


class CartResponse(CartBase):
    id: UUID = Field(..., description="Unique identifier of the cart")
    total: Decimal = Field(..., description="Total amount of the cart")

    created_at: datetime = Field(..., description="Datetime when the cart was created")
    updated_at: datetime = Field(
        ..., description="Datetime when the cart was last updated"
    )
    version: int = Field(
        ..., description="Version number for optimistic concurrency control"
    )

    items: List[CartItemResponse] = Field(
        default_factory=list, description="List of items in the cart"
    )


CartResponse.model_rebuild()
