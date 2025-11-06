from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional


class ProductMediaBase(BaseModel):
    variant_id: Optional[UUID] = Field(None, description="ID of the product variant")
    is_primary: bool = Field(
        False, description="Indicates if the media is the primary media for the product"
    )
    model_config = ConfigDict(from_attributes=True)


class ProductMediaCreate(ProductMediaBase):
    media_id: UUID = Field(..., description="ID of the media")


class ProductMediaUpdate(BaseModel):
    variant_id: Optional[UUID] = Field(None, description="ID of the product variant")
    is_primary: Optional[bool] = Field(
        None, description="Indicates if the media is the primary media for the product"
    )


class ProductMediaResponse(ProductMediaBase):
    product_id: UUID = Field(..., description="ID of the product")
    id: UUID = Field(..., description="Unique identifier of the product media")
    uploaded_at: datetime = Field(
        ..., description="Timestamp when the media was associated with the product"
    )


class ProductMediaRef(BaseModel):
    """Lightweight reference to an existing Media used in nested create payloads."""

    product_id: UUID = Field(..., description="ID of the product")
    media_id: UUID = Field(..., description="ID of the media")
    order: Optional[int] = Field(
        None, description="Order of the media in the product gallery", ge=0
    )
    is_primary: bool = Field(
        False, description="Indicates if the media is the primary media for the product"
    )
