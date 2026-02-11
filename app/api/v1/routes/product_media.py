from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Path
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.logs.logging_utils import get_logger

from app.db.session import get_session
from app.schemas.product_media import (
    ProductMediaCreate,
    ProductMediaUpdate,
    ProductMediaResponse,
)
from app.services.product_media import ProductMediaService

logger = get_logger("app.product_media")

router = APIRouter(prefix="/products/{product_id}/media", tags=["Product Media"])


@router.post(
    "", response_model=ProductMediaResponse, status_code=status.HTTP_201_CREATED
)
async def create_media_association(
    product_id: UUID,
    payload: ProductMediaCreate,
    session: AsyncSession = Depends(get_session),
) -> ProductMediaResponse:
    service = ProductMediaService(session)
    try:
        pm = await service.create(
            product_id=product_id,
            media_id=payload.media_id,
            variant_id=payload.variant_id,
            is_primary=bool(payload.is_primary),
        )
        return ProductMediaResponse.model_validate(pm)
    except IntegrityError:
        logger.debug(
            "IntegrityError on creating product-media association",
            extra={"product_id": str(product_id), "payload": payload.model_dump()},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Constraint violated or duplicate product-media association",
        )


@router.get("", response_model=List[ProductMediaResponse])
async def get_media_for_product(
    product_id: UUID, session: AsyncSession = Depends(get_session)
) -> List[ProductMediaResponse]:
    service = ProductMediaService(session)
    orm_items = await service.list(product_id)
    return [ProductMediaResponse.model_validate(item) for item in orm_items]


@router.get("/{pm_id}", response_model=ProductMediaResponse)
async def get_media_assoc(
    product_id: UUID,
    pm_id: UUID = Path(..., description="ProductMedia id"),
    session: AsyncSession = Depends(get_session),
) -> ProductMediaResponse:
    service = ProductMediaService(session)
    pm = await service.get(pm_id)
    if not pm or pm.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ProductMedia not found"
        )
    return ProductMediaResponse.model_validate(pm)


@router.patch("/{pm_id}", response_model=ProductMediaResponse)
async def patch_media_assoc(
    product_id: UUID,
    payload: ProductMediaUpdate,
    session: AsyncSession = Depends(get_session),
    pm_id: UUID = Path(..., description="ProductMedia id"),
) -> ProductMediaResponse:
    service = ProductMediaService(session)
    pm = await service.get(pm_id)
    if not pm or pm.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ProductMedia not found"
        )

    try:
        updated = await service.update(
            pm,
            variant_id=payload.variant_id,
            is_primary=payload.is_primary,
        )
        return ProductMediaResponse.model_validate(updated)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update violates database constraints (possible race or duplicate)",
        )


@router.delete("/{pm_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_media_assoc(
    product_id: UUID,
    pm_id: UUID = Path(..., description="ProductMedia id"),
    session: AsyncSession = Depends(get_session),
):
    service = ProductMediaService(session)
    pm = await service.get(pm_id)
    if not pm or pm.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="ProductMedia not found"
        )

    await service.delete(pm)
    return None
