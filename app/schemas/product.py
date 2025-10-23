from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, TYPE_CHECKING, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

from .media import ProductMediaResponse, ProductMediaRef

if TYPE_CHECKING:
    from app.schemas.product import (
        ProductResponse,
        ProductVariantResponse,
    )


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
    is_active: bool = Field(True, description="Indicates if the product is active")
    stock: int = Field(0, description="Stock quantity of the product")
    attributes: Optional[Dict[str, str]] = Field(
        None, description="Custom attributes for the product"
    )
    primary_image_id: Optional[UUID] = Field(
        None, description="ID of the primary image for the product"
    )


class ProductCreate(ProductBase):
    pass


class ProductCreateNested(ProductCreate):
    variants: Optional[List[ProductVariantCreate]] = Field(
        None, description="List of product variants"
    )
    media: Optional[List[ProductMediaRef]] = Field(
        None, description="List of product media"
    )


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
    variants: Optional[List[ProductVariantResponse]] = Field(
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


# Product Variant Schemas
class ProductVariantBase(BaseModel):
    sku: Optional[str] = Field(
        None, description="Stock Keeping Unit of the product variant"
    )
    name: str = Field(..., description="Name of the product variant")
    price: Decimal = Field(..., description="Price of the product variant")
    stock: int = Field(0, description="Stock quantity of the product variant")
    attributes: Optional[Dict[str, str]] = Field(
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
    model_config = ConfigDict(
        from_attributes=True, json_encoders={Decimal: lambda v: str(v)}
    )


ProductResponse.model_rebuild()
ProductVariantResponse.model_rebuild()
ProductCreateNested.model_rebuild()
ProductVariantCreate.model_rebuild()
