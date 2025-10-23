from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


class MediaBase(BaseModel):
    file_url: str = Field(..., description="URL of the media file")
    alt_text: str | None = Field(None, description="Alternative text for the media")
    mime_type: str = Field(..., description="MIME type of the media file")
    uploaded_by: UUID = Field(..., description="ID of the user who uploaded the media")


class MediaCreate(MediaBase):
    pass


class MediaResponse(MediaBase):
    id: UUID = Field(..., description="Unique identifier of the media")
    uploaded_at: datetime = Field(
        ..., description="Timestamp when the media was uploaded"
    )
    model_config = ConfigDict(from_attributes=True)


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
    model_config = ConfigDict(from_attributes=True)


class ProductMediaRef(BaseModel):
    """Lightweight reference to an existing Media used in nested create payloads."""

    media_id: UUID = Field(..., description="ID of the media")
    order: int = Field(..., description="Order of the media in the product gallery")
    is_primary: bool = Field(
        False, description="Indicates if the media is the primary media for the product"
    )
