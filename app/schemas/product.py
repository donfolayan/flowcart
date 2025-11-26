from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, List, TYPE_CHECKING
from datetime import datetime
from uuid import UUID
from decimal import Decimal
from app.schemas.product_variant import ProductVariantResponse, ProductVariantCreate

from .product_media import ProductMediaResponse

if TYPE_CHECKING:
    from .category import CategoryMinimalResponse


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
    attributes: Optional[Dict[str, List[str]]] = Field(
        None, description="Custom attributes for the product"
    )
    category_id: Optional[UUID] = Field(
        None, description="ID of the category the product belongs to"
    )
    category: Optional["CategoryMinimalResponse"] = Field(
        None, description="Category details of the product"
    )
    primary_image_id: Optional[UUID] = Field(
        None, description="ID of the primary image for the product"
    )
    variants: Optional[List[ProductVariantCreate]] = Field(
        None, description="List of variants associated with the product"
    )
    variant_ids: Optional[List[UUID]] = Field(
        None, description="List of variant IDs associated with the product"
    )
    media: Optional[List[UUID]] = Field(
        None, description="List of media IDs associated with the product"
    )

    model_config = ConfigDict(from_attributes=True)


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    """All fields optional for partial updates"""

    name: Optional[str] = Field(None, max_length=100, description="Name of the product")
    slug: Optional[str] = Field(
        None, max_length=120, description="URL-friendly slug for the product"
    )
    description: Optional[str] = Field(None, description="Description of the product")
    base_price: Optional[Decimal] = Field(None, description="Base price of the product")
    sku: Optional[str] = Field(None, description="Stock Keeping Unit of the product")
    is_variable: Optional[bool] = Field(
        None, description="Indicates if the product has variants"
    )
    status: Optional[str] = Field(None, description="Status of the product")
    stock: Optional[int] = Field(None, description="Stock quantity of the product")
    attributes: Optional[Dict[str, str]] = Field(
        None, description="Custom attributes for the product"
    )
    primary_image_id: Optional[UUID] = Field(
        None, description="ID of the primary image for the product"
    )
    variants: Optional[List[ProductVariantCreate]] = Field(
        None, description="List of variants associated with the product"
    )
    variant_ids: Optional[List[UUID]] = Field(
        None, description="List of variant IDs associated with the product"
    )
    media: Optional[List[UUID]] = Field(
        None, description="List of media IDs associated with the product"
    )


class ProductResponse(ProductBase):
    id: UUID = Field(..., description="Unique identifier of the product")
    created_at: datetime = Field(
        ..., description="Timestamp when the product was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the product was last updated"
    )
    variants: Optional[List["ProductVariantResponse"]] = Field(  # type: ignore[assignment]
        None, description="List of product variants"
    )
    media: Optional[List[ProductMediaResponse]] = Field(  # type: ignore[assignment]
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
