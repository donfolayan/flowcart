from typing import List
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.product import Product
from app.models.media import Media
from app.models.product_media import ProductMedia
from app.core.logs.logging_utils import get_logger

logger = get_logger("app.product_media_service")


async def _validate_media_and_add(
    db: AsyncSession, product: Product, media_ids: List[UUID]
) -> None:
    """Validate media ids exist, then add missing ProductMedia associations."""
    if not media_ids:
        return

    q = select(Media).where(Media.id.in_(media_ids))
    r = await db.execute(q)
    found_media = {m.id: m for m in r.scalars().all()}
    missing_media = set(media_ids) - set(found_media.keys())
    if missing_media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Some media items not found: {', '.join(str(m) for m in missing_media)}",
        )

    # Determine current associations and only add the missing ones
    q = select(ProductMedia).where(ProductMedia.product_id == product.id)
    r = await db.execute(q)
    current_media_ids = {pm.media_id for pm in r.scalars().all()}

    to_add = set(media_ids) - current_media_ids
    for mid in to_add:
        db.add(ProductMedia(product_id=product.id, media_id=mid))


async def get_product_media(session: AsyncSession, pm_id):
    q = select(ProductMedia).where(ProductMedia.id == pm_id)
    res = await session.execute(q)
    pm = res.scalar_one_or_none()
    return pm


async def list_product_media(session: AsyncSession, product_id):
    q = (
        select(ProductMedia)
        .where(ProductMedia.product_id == product_id)
        .order_by(ProductMedia.is_primary.desc(), ProductMedia.uploaded_at)
    )
    res = await session.execute(q)
    return res.scalars().all()


async def create_product_media(
    session: AsyncSession, product_id, media_id, variant_id=None, is_primary=False
):
    # validate product exists
    res = await session.execute(select(Product).where(Product.id == product_id))
    product = res.scalar_one_or_none()
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # validate media exists
    res = await session.execute(select(Media).where(Media.id == media_id))
    media = res.scalar_one_or_none()
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    if is_primary:
        await session.execute(
            update(ProductMedia)
            .where(ProductMedia.product_id == product_id, ProductMedia.is_primary)
            .values(is_primary=False)
        )

    pm = ProductMedia(
        product_id=product_id,
        media_id=media_id,
        variant_id=variant_id,
        is_primary=is_primary,
    )
    session.add(pm)
    try:
        await session.flush()
    except IntegrityError as e:
        logger.debug(
            "IntegrityError on creating product-media association",
            extra={"product_id": str(product_id), "media_id": str(media_id), "variant_id": str(variant_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Duplicate product-media association or constraint violated: {e.orig}",
        )
    await session.refresh(pm)
    return pm


async def update_product_media(
    session: AsyncSession, pm: ProductMedia, *, variant_id=None, is_primary=None
):
    if variant_id is not None:
        pm.variant_id = variant_id

    if is_primary is not None and is_primary != pm.is_primary:
        if is_primary:
            # unset other primary for this product
            await session.execute(
                update(ProductMedia)
                .where(
                    ProductMedia.product_id == pm.product_id, ProductMedia.is_primary
                )
                .values(is_primary=False)
            )
        pm.is_primary = is_primary

    session.add(pm)
    try:
        await session.flush()
    except IntegrityError:
        logger.debug(
            "IntegrityError on updating product-media association",
            extra={"pm_id": str(pm.id), "variant_id": str(variant_id), "is_primary": is_primary},
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Update violates database constraints",
        )
    await session.refresh(pm)
    return pm


async def delete_product_media(session: AsyncSession, pm: ProductMedia):
    await session.delete(pm)
