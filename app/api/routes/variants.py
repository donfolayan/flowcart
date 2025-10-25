from uuid import UUID
from typing import List
from fastapi import APIRouter, status, HTTPException
from sqlalchemy import select
from app.models.product import ProductVariant
from app.schemas.product import ProductVariantResponse

router = APIRouter(
    prefix="/variants",
    tags=["variants"],
)


@router.get(
    "/{variant_id}",
    description="Get product variant by ID",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_200_OK,
)
async def get_product_variant(variant_id: UUID) -> ProductVariantResponse:
    q = select(ProductVariant).where(ProductVariant.id == variant_id)
    r = await ProductVariant.execute(q)
    variant = r.scalars().one_or_none()

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found"
        )

    return variant


@router.get(
    "/{product_id}",
    description="Get all variants for a product",
    response_model=List[ProductVariantResponse],
    status_code=status.HTTP_200_OK,
)
async def get_product_variants(product_id: UUID) -> List[ProductVariantResponse]:
    q = select(ProductVariant).where(ProductVariant.product_id == product_id)
    r = await ProductVariant.execute(q)
    variants = r.scalars().all()
    return variants
