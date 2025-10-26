from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_admin
from app.db.session import get_session
from app.models.product import Product, ProductVariant
from app.schemas.product_variant import ProductVariantResponse, ProductVariantCreate

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
async def get_product_variant(
    variant_id: UUID, db: AsyncSession = Depends(get_session)
) -> ProductVariantResponse:
    q = select(ProductVariant).where(ProductVariant.id == variant_id)
    r = await db.execute(q)
    variant: Optional[ProductVariant] = r.scalars().one_or_none()

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found"
        )

    return variant


@router.get(
    "/product/{product_id}",
    description="Get all variants for a product",
    response_model=List[ProductVariantResponse],
    status_code=status.HTTP_200_OK,
)
async def get_product_variants(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> List[ProductVariantResponse]:
    q = select(ProductVariant).where(ProductVariant.product_id == product_id)
    r = await db.execute(q)
    variants: List[ProductVariant] = list(r.scalars().all())
    return [ProductVariantResponse.model_validate(variant) for variant in variants]


@router.post(
    "/{product_id}",
    description="Create a new product variant",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_product_variant(
    payload: ProductVariantCreate,
    product_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> ProductVariantResponse:
    payload_data = payload.model_dump()

    if not payload_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload - no data provided",
        )

    product_query = select(Product).where(Product.id == product_id)
    result_query = await db.execute(product_query)
    base_product = result_query.scalars().one_or_none()

    if base_product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Base product not found"
        )

    variant = ProductVariant(**payload_data, product_id=product_id)
    variant.product_id = product_id

    try:
        db.add(variant)
        await db.commit()
        await db.refresh(variant)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product variant",
        ) from e

    response.headers["Location"] = f"/variants/{variant.id}"
    return ProductVariantResponse.model_validate(variant)
