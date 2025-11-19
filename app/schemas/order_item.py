from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class OrderItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: UUID = Field(..., description="Unique identifier of the product")
    variant_id: Optional[UUID] = Field(
        None, description="Unique identifier of the product variant"
    )
    product_name: str = Field(..., description="Name of the product")
    product_image_url: Optional[str] = Field(
        None, description="URL of the product image"
    )
    sku: str = Field(..., description="Stock Keeping Unit of the product")
    quantity: int = Field(..., description="Quantity of the product ordered")
    unit_price_cents: int = Field(..., description="Unit price of the product in cents")
    line_total_cents: int = Field(
        ..., description="Total line amount for this item in cents"
    )


class OrderItemCreate(OrderItemBase):
    pass


class OrderItemUpdate(BaseModel):
    quantity: Optional[int] = Field(None, description="Quantity of the product ordered")


class OrderItemResponse(OrderItemBase):
    id: UUID = Field(..., description="Unique identifier of the order item")
    order_id: UUID = Field(..., description="Unique identifier of the associated order")
    created_at: datetime = Field(
        ..., description="Creation timestamp of the order item"
    )
    updated_at: datetime = Field(
        ..., description="Last update timestamp of the order item"
    )
