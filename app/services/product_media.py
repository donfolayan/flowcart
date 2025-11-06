from typing import List
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.product import Product
from app.models.media import Media
from app.models.product_media import ProductMedia


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
