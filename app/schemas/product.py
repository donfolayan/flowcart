from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.schemas.product_variant import ProductVariantResponse

from .media import ProductMediaResponse


# Product Schemas
class ProductBase(BaseModel):
    name: str = Field(..., max_length=100, description="Name of the product")
    slug: Optional[str] = Field(
        None, max_length=120, description="URL-friendly slug for the product"
    )
    description: Optional[str] = Field(None, description="Description of the product")
    base_price: Optional[Decimal] = Field(None, description="Base price of the product")
    sku: Optional[str] = Field(None, description="Stock Keeping Unit of the product")
    is_variable: bool = Field(
        False, description="Indicates if the product has variants"
    )
    status: str = Field("draft", description="Status of the product")
    stock: int = Field(0, description="Stock quantity of the product")
    attributes: Optional[Dict[str, str]] = Field(
        None, description="Custom attributes for the product"
    )
    primary_image_id: Optional[UUID] = Field(
        None, description="ID of the primary image for the product"
    )


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: UUID = Field(..., description="Unique identifier of the product")
    created_at: datetime = Field(
        ..., description="Timestamp when the product was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the product was last updated"
    )
    variants: Optional[List["ProductVariantResponse"]] = Field(
        None, description="List of product variants"
    )
    media: Optional[List[ProductMediaResponse]] = Field(
        None, description="List of product media", alias="media_associations"
    )
    model_config = ConfigDict(
        from_attributes=True, json_encoders={Decimal: lambda v: str(v)}
    )


class ProductMinimalResponse(ProductBase):
    id: UUID = Field(..., description="Unique identifier of the product")
    created_at: datetime = Field(
        ..., description="Timestamp when the product was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the product was last updated"
    )


ProductResponse.model_rebuild()
ProductCreate.model_rebuild()
ProductUpdate.model_rebuild()
