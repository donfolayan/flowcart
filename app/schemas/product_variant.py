from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, List
from uuid import UUID
from decimal import Decimal

from .product_media import ProductMediaResponse


class ProductVariantBase(BaseModel):
    sku: Optional[str] = Field(
        None, description="Stock Keeping Unit of the product variant"
    )
    name: str = Field(..., description="Name of the product variant")
    price: Optional[Decimal] = Field(None, description="Price of the product variant")
    stock: int = Field(0, description="Stock quantity of the product variant")
    status: str = Field("draft", description="Status of the product variant")
    attributes: Optional[Dict[str, List[str]]] = Field(
        None, description="Custom attributes for the product variant"
    )
    primary_image_id: Optional[UUID] = Field(
        None, description="ID of the primary image for the product variant"
    )


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantResponse(ProductVariantBase):
    id: UUID = Field(..., description="Unique identifier of the product variant")
    media: Optional[List[ProductMediaResponse]] = Field(
        None, description="List of product media", alias="media_associations"
    )
    model_config = ConfigDict(from_attributes=True)


ProductVariantResponse.model_rebuild()
ProductVariantCreate.model_rebuild()
