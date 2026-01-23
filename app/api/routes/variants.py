from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.permissions import require_admin
from app.db.session import get_session
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.schemas.product_variant import ProductVariantResponse, ProductVariantCreate
from app.core.logs.logging_utils import get_logger

logger = get_logger("app.variant")

router = APIRouter(
    prefix="/variants",
    tags=["Variants"],
)
admin_router = APIRouter(
    prefix="/admin/variants",
    tags=["Admin Variants"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/{variant_id}",
    description="Get product variant by ID",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_200_OK,
)
async def get_product_variant_by_id(
    variant_id: UUID, db: AsyncSession = Depends(get_session)
) -> ProductVariantResponse:
    q = select(ProductVariant).where(ProductVariant.id == variant_id)
    r = await db.execute(q)
    variant: Optional[ProductVariant] = r.scalars().one_or_none()

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found"
        )

    return ProductVariantResponse.model_validate(variant)


@router.get(
    "/product/{product_id}",
    description="Get all variants for a product",
    response_model=List[ProductVariantResponse],
    status_code=status.HTTP_200_OK,
)
async def get_product_variants_by_product_id(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> List[ProductVariantResponse]:
    q = select(ProductVariant).where(ProductVariant.product_id == product_id)
    r = await db.execute(q)
    variants: List[ProductVariant] = list(r.scalars().all())
    return [ProductVariantResponse.model_validate(variant) for variant in variants]


@admin_router.post(
    "/{product_id}",
    description="Create a new product variant",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_201_CREATED,
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
        logger.exception(
            "Failed to create product variant",
            extra={"product_id": str(product_id), "payload": payload.model_dump()},
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create product variant",
        ) from e

    response.headers["Location"] = f"/variants/{variant.id}"
    return ProductVariantResponse.model_validate(variant)


@admin_router.delete(
    "/{variant_id}",
    description="Delete a product variant",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product_variant(
    variant_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    q = select(ProductVariant).where(ProductVariant.id == variant_id)
    r = await db.execute(q)
    variant: Optional[ProductVariant] = r.scalars().one_or_none()

    if not variant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product variant not found"
        )

    try:
        await db.execute(delete(ProductVariant).where(ProductVariant.id == variant_id))
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Failed to delete product variant",
            extra={"variant_id": str(variant_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product variant",
        ) from e


@admin_router.delete(
    "/product/{product_id}",
    description="Delete all variants for a product",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product_variants(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    q = select(ProductVariant).where(ProductVariant.product_id == product_id).limit(1)
    r = await db.execute(q)
    exists: ProductVariant = r.scalars().one_or_none()

    if not exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No variants found for the product",
        )

    try:
        query = delete(ProductVariant).where(ProductVariant.product_id == product_id)
        await db.execute(query)
        await db.commit()
    except IntegrityError as e:
        logger.debug(
            "IntegrityError on deleting product variants",
            extra={"product_id": str(product_id)},
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete product variants due to existing dependencies",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Failed to delete product variants",
            extra={"product_id": str(product_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product variants",
        ) from e
