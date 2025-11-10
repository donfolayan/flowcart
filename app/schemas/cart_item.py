from pydantic import BaseModel, ConfigDict, Field
from decimal import Decimal
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.enums.currency_enums import CurrencyEnum


class CartItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cart_id: UUID = Field(..., description="ID of the cart to which the item belongs")

    product_id: UUID = Field(..., description="ID of the product")
    variant_id: Optional[UUID] = Field(
        None, description="ID of the product variant, if applicable"
    )
    product_name: str = Field(..., description="Name of the product")
    product_snapshot: Optional[dict] = Field(
        default={},
        description="Snapshot of the product details at the time of adding to cart",
    )

    quantity: int = Field(
        default=1, gt=0, description="Quantity of the product in the cart item"
    )

    unit_price_currency: CurrencyEnum = Field(
        default=CurrencyEnum.USD, description="Currency of the unit price"
    )
    unit_price: Decimal = Field(
        default_factory=lambda: Decimal("0.00"), description="Unit price of the product"
    )
    tax_amount: Decimal = Field(
        default_factory=lambda: Decimal("0.00"),
        description="Tax amount for the cart item",
    )
    discount_amount: Decimal = Field(
        default_factory=lambda: Decimal("0.00"),
        description="Discount amount for the cart item",
    )


class CartItemCreate(CartItemBase):
    pass


class CartItemUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    quantity: Optional[int] = Field(
        None, gt=0, description="Quantity of the product in the cart item"
    )
    unit_price: Optional[Decimal] = Field(None, description="Unit price of the product")
    tax_amount: Optional[Decimal] = Field(
        None, description="Tax amount for the cart item"
    )
    discount_amount: Optional[Decimal] = Field(
        None, description="Discount amount for the cart item"
    )
    line_total: Optional[Decimal] = Field(
        None,
        description="Total amount for this cart item (unit price * quantity - discount + tax)",
    )


class CartItemResponse(CartItemBase):
    id: UUID = Field(..., description="Unique identifier of the cart item")
    line_total: Decimal = Field(
        ...,
        description="Total amount for this cart item (unit price * quantity - discount + tax)",
    )
    created_at: datetime = Field(
        ..., description="Datetime when the cart item was created"
    )
    updated_at: datetime = Field(
        ..., description="Datetime when the cart item was last updated"
    )


CartItemResponse.model_rebuild()
