from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_admin
from app.db.session import get_session
from app.schemas.product_variant import (
    ProductVariantResponse,
    ProductVariantCreate,
    ProductVariantUpdate,
)
from app.services.variant import VariantService

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
    service = VariantService(db)
    variant = await service.get_by_id(variant_id=variant_id)
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
    service = VariantService(db)
    variants = await service.list_by_product(product_id=product_id)
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
    service = VariantService(db)
    variant = await service.create(product_id=product_id, payload=payload)

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
    service = VariantService(db)
    await service.delete(variant_id=variant_id)


@admin_router.delete(
    "/product/{product_id}",
    description="Delete all variants for a product",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product_variants(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    service = VariantService(db)
    await service.delete_by_product(product_id=product_id)


@admin_router.patch(
    "/{variant_id}",
    description="Update a product variant",
    response_model=ProductVariantResponse,
    status_code=status.HTTP_200_OK,
)
async def update_product_variant(
    variant_id: UUID,
    payload: ProductVariantUpdate,
    db: AsyncSession = Depends(get_session),
) -> ProductVariantResponse:
    service = VariantService(db)
    variant = await service.update(variant_id=variant_id, payload=payload)
    return ProductVariantResponse.model_validate(variant)
