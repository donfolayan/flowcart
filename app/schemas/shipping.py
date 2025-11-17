from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.enums.carrier_enum import CarrierEnum
from app.enums.shipping_status_enum import ShippingStatusEnum


class ShippingBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    shipping_cents: int = Field(..., description="Shipping cost in cents", ge=0)
    shipping_tax_cents: int = Field(0, description="Shipping tax amount in cents", ge=0)
    carrier: CarrierEnum = Field(..., description="Shipping carrier")
    status: ShippingStatusEnum = Field(
        ShippingStatusEnum.PENDING, description="Current shipping status"
    )
    tracking_number: Optional[str] = Field(
        None, description="Tracking number for the shipment", max_length=100
    )
    tracking_url: Optional[str] = Field(
        None, description="URL to track the shipment", max_length=255
    )
    label_url: Optional[str] = Field(
        None, description="URL to the shipping label", max_length=255
    )


class ShippingCreate(ShippingBase):
    order_id: UUID = Field(..., description="Unique identifier of the associated order")
    address_id: Optional[UUID] = Field(
        None, description="Unique identifier of the shipping address"
    )


class ShippingUpdate(BaseModel):
    status: Optional[ShippingStatusEnum] = Field(
        None, description="Updated shipping status"
    )
    tracking_number: Optional[str] = Field(
        None, description="Updated tracking number", max_length=100
    )
    tracking_url: Optional[str] = Field(
        None, description="Updated tracking URL", max_length=255
    )
    shipped_at: Optional[datetime] = Field(
        None, description="Timestamp when shipment was dispatched"
    )
    delivered_at: Optional[datetime] = Field(
        None, description="Timestamp when shipment was delivered"
    )


class ShippingResponse(ShippingBase):
    id: UUID = Field(..., description="Unique identifier of the shipping record")
    order_id: UUID = Field(..., description="Unique identifier of the associated order")
    address_id: Optional[UUID] = Field(
        None, description="Unique identifier of the shipping address"
    )
    shipped_at: Optional[datetime] = Field(
        None, description="Timestamp when shipment was dispatched"
    )
    delivered_at: Optional[datetime] = Field(
        None, description="Timestamp when shipment was delivered"
    )
    created_at: datetime = Field(
        ..., description="Creation timestamp of the shipping record"
    )
    updated_at: datetime = Field(
        ..., description="Last update timestamp of the shipping record"
    )
