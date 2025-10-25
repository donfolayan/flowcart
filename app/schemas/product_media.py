from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


class ProductMediaBase(BaseModel):
    product_id: UUID = Field(..., description="ID of the product")
    media_id: UUID = Field(..., description="ID of the media")
    variant_id: UUID | None = Field(None, description="ID of the product variant")
    is_primary: bool = Field(
        False, description="Indicates if the media is the primary media for the product"
    )


class ProductMediaCreate(ProductMediaBase):
    pass


class ProductMediaResponse(ProductMediaBase):
    id: UUID = Field(..., description="Unique identifier of the product media")
    uploaded_at: datetime = Field(
        ..., description="Timestamp when the media was associated with the product"
    )
    model_config = ConfigDict(from_attributes=True)


class ProductMediaRef(BaseModel):
    """Lightweight reference to an existing Media used in nested create payloads."""

    media_id: UUID = Field(..., description="ID of the media")
    order: int = Field(..., description="Order of the media in the product gallery")
    is_primary: bool = Field(
        False, description="Indicates if the media is the primary media for the product"
    )
