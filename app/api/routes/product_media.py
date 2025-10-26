from sqlalchemy.exc import IntegrityError
from uuid import UUID
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.models.product_media import ProductMedia
from app.core.permissions import require_admin
from app.models.product import Product
from app.models.media import Media
from app.schemas.product_media import ProductMediaResponse

router = APIRouter(
    prefix="/product-media",
    tags=["product-media"],
)


@router.get(
    "/{product_id}",
    description="Get all media for a product",
    response_model=List[ProductMediaResponse],
    status_code=status.HTTP_200_OK,
)
async def get_all_product_media(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> List[ProductMediaResponse]:
    # Check if the product exists
    product_query = select(Product).where(Product.id == product_id)
    product_result = await db.execute(product_query)
    product: Optional[Product] = product_result.scalars().one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Fetch all media associated with the product
    q = select(ProductMedia).where(ProductMedia.product_id == product_id)
    r = await db.execute(q)
    media_items: List[ProductMedia] = list(r.scalars().all())

    return [ProductMediaResponse.model_validate(media) for media in media_items]


@router.post(
    "/",
    description="Associate media with a product",
    response_model=ProductMediaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def associate_media_with_product(
    product_id: UUID,
    media_id: UUID,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> ProductMediaResponse:
    # Check if the product exists
    product_query = select(Product).where(Product.id == product_id)
    product_result = await db.execute(product_query)
    product: Optional[Product] = product_result.scalars().one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Check if the media exists
    media_query = select(Media).where(Media.id == media_id).limit(1)
    media_result = await db.execute(media_query)
    media: Optional[Media] = media_result.scalars().one_or_none()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    # Prevent duplicate association
    q_check = (
        select(ProductMedia)
        .where(
            ProductMedia.product_id == product.id,
            ProductMedia.media_id == media.id,
        )
        .limit(1)
    )
    r_check = await db.execute(q_check)
    existing = r_check.scalars().one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Media is already associated with this product",
        )

    # Associate media with product
    product_media = ProductMedia(product_id=product.id, media_id=media.id)
    db.add(product_media)
    try:
        await db.commit()
        await db.refresh(product_media)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot associate media with product due to existing dependencies",
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to associate media with product",
        ) from e

    response.headers["Location"] = f"/product-media/{product_media.id}"
    return ProductMediaResponse.model_validate(product_media)


@router.delete(
    "/{product_media_id}",
    description="Delete a product media association",
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_product_media_association(
    product_media_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    q = select(ProductMedia).where(ProductMedia.id == product_media_id).limit(1)
    r = await db.execute(q)
    product_media: Optional[ProductMedia] = r.scalars().one_or_none()

    if not product_media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product media association not found",
        )

    try:
        await db.delete(product_media)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete product media association due to existing dependencies",
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product media association",
        ) from e
