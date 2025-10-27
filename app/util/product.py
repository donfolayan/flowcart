from typing import List
from uuid import UUID
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.media import Media
from app.models.product_media import ProductMedia


async def _attach_existing_variants(
    db: AsyncSession, product: Product, ids: List[UUID]
) -> None:
    """Validate incoming variant ids and bulk attach them to the product."""
    if not ids:
        return

    q = select(ProductVariant).where(ProductVariant.id.in_(ids))
    r = await db.execute(q)
    found = {v.id: v for v in r.scalars().all()}

    missing = set(ids) - set(found.keys())
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Some variants not found: {', '.join(str(x) for x in missing)}",
        )

    conflicting = [str(v.id) for v in found.values() if v.product_id is not None]
    if conflicting:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Some variants are already associated with another product and cannot be reused: {', '.join(conflicting)}",
        )

    new_variant_status = "active" if product.status == "active" else "draft"
    await db.execute(
        update(ProductVariant)
        .where(ProductVariant.id.in_(ids))
        .values(product_id=product.id, status=new_variant_status)
    )


async def _create_inline_variants(
    db: AsyncSession, product: Product, variants: List[dict]
) -> List[ProductVariant]:
    """Create inline variant dicts (from Pydantic.model_dump()) and attach to product."""
    created = []
    for v in variants:
        create_data = {k: v for k, v in v.items() if k != "id"}
        create_data.setdefault("product_id", product.id)
        create_data.setdefault(
            "status", "active" if product.status == "active" else "draft"
        )
        new_variant = ProductVariant(**create_data)
        db.add(new_variant)
        created.append(new_variant)
    return created


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


async def _product_has_variants(db: AsyncSession, product_id: UUID) -> bool:
    q = select(ProductVariant).where(ProductVariant.product_id == product_id).limit(1)
    r = await db.execute(q)
    return r.scalars().one_or_none() is not None
