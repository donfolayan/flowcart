from pydantic import BaseModel, ConfigDict
from typing import Optional, TYPE_CHECKING, List
from datetime import datetime
from uuid import UUID
from decimal import Decimal

if TYPE_CHECKING:
    from app.schemas.product import (
        ProductResponse,
        ProductVariantResponse,
        ProductImageResponse,
    )


# Product Schemas
class ProductBase(BaseModel):
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    base_price: Optional[Decimal] = None
    sku: Optional[str] = None
    is_variable: bool = False
    is_active: bool = True
    stock: int = 0
    attributes: Optional[dict] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(ProductBase):
    pass


class ProductResponse(ProductBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    images: Optional[List["ProductImageResponse"]] = None
    variants: Optional[List["ProductVariantResponse"]] = None
    model_config = ConfigDict(
        from_attributes=True, json_encoders={Decimal: lambda v: str(v)}
    )


# Product Variant Schemas
class ProductVariantBase(BaseModel):
    product_id: UUID
    sku: Optional[str] = None
    name: str
    price: Decimal
    stock: int = 0
    attributes: Optional[dict] = None
    image_url: Optional[str] = None


class ProductVariantCreate(ProductVariantBase):
    pass


class ProductVariantResponse(ProductVariantBase):
    id: UUID
    images: Optional[List["ProductImageResponse"]] = None
    model_config = ConfigDict(
        from_attributes=True, json_encoders={Decimal: lambda v: str(v)}
    )


# Product Image Schemas
class ProductImageBase(BaseModel):
    product_id: UUID
    alt_text: Optional[str] = None
    image_url: Optional[str] = None
    is_variant_image: bool = False
    variant_id: Optional[UUID] = None


class ProductImageCreate(ProductImageBase):
    pass


class ProductImageResponse(ProductImageBase):
    id: UUID
    model_config = ConfigDict(from_attributes=True)


ProductResponse.model_rebuild()
ProductVariantResponse.model_rebuild()
ProductImageResponse.model_rebuild()
