from typing import List, Optional
from uuid import UUID
import uuid
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from sqlalchemy import delete
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload
from app.core.logs.logging_utils import get_logger
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_media import ProductMedia
from app.schemas.product import ProductCreate, ProductUpdate
from app.schemas.product_variant import ProductVariantCreate
from app.services.product_media import _validate_media_and_add


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


async def _product_has_variants(db: AsyncSession, product_id: UUID) -> bool:
    q = select(ProductVariant).where(ProductVariant.product_id == product_id).limit(1)
    r = await db.execute(q)
    return r.scalars().one_or_none() is not None


logger = get_logger("app.product")


class ProductService:
    """Business logic for products."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(self, skip: int = 0, limit: int = 50) -> List[Product]:
        """List products with pagination."""
        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.variants)
                .selectinload(ProductVariant.media_associations)
                .selectinload(ProductMedia.media),
            )
            .offset(skip)
            .limit(limit)
            .order_by(Product.created_at.desc())
        )
        return list(result.scalars().all())

    async def get(self, product_id: UUID) -> Product:
        """Get a single product by ID."""
        q = (
            select(Product)
            .where(Product.id == product_id)
            .options(
                selectinload(Product.variants)
                .selectinload(ProductVariant.media_associations)
                .selectinload(ProductMedia.media)
            )
        )
        result = await self.db.execute(q)
        product = result.scalars().first()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )
        return product

    async def create(self, payload: ProductCreate) -> Product:
        data = payload.model_dump(exclude_unset=True)

        inline_variants: Optional[List[ProductVariantCreate]] = data.pop(
            "variants", None
        )
        variant_ids: Optional[List[UUID]] = data.pop("variant_ids", None)
        media_ids = data.pop("media", None)

        if data.get("status", "draft") == "active":
            is_variable = data.get("is_variable", False)
            has_variants_provided = inline_variants not in (
                None,
                [],
            ) or variant_ids not in (None, [])
            if is_variable and not has_variants_provided:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="At least one variant is required for variable products.",
                )
        if not data.get("is_variable", False) and data.get("base_price", None) is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Base price is required for non-variable products.",
            )

        try:
            product = Product(**{k: v for k, v in data.items()})
            self.db.add(product)
            await self.db.flush()

            if variant_ids:
                await _attach_existing_variants(self.db, product, variant_ids)

            if inline_variants:
                normalized = []
                for v in inline_variants:
                    if hasattr(v, "model_dump"):
                        normalized.append(v.model_dump())
                    elif isinstance(v, dict):
                        normalized.append(dict(v))
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid variant payload",
                        )
                await _create_inline_variants(self.db, product, normalized)

            if product.status == "active" and product.is_variable:
                missing = []
                if variant_ids:
                    q = select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
                    r = await self.db.execute(q)
                    for vv in r.scalars().all():
                        if vv.price is None:
                            missing.append(str(vv.id))
                for i, nv in enumerate(inline_variants or []):
                    d = (
                        nv.model_dump()
                        if hasattr(nv, "model_dump")
                        else (nv if isinstance(nv, dict) else {})
                    )
                    if d.get("price") is None:
                        missing.append(f"(new index {i})")
                if missing:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=(
                            "All variants must have a price for active products. "
                            f"Missing prices for: {', '.join(missing)}"
                        ),
                    )

            if media_ids is not None:
                if media_ids == []:
                    await self.db.execute(
                        delete(ProductMedia).where(
                            ProductMedia.product_id == product.id
                        )
                    )
                else:
                    await _validate_media_and_add(self.db, product, media_ids)

            max_retries = 3
            for attempt in range(max_retries + 1):
                try:
                    await self.db.flush()
                    await self.db.commit()
                    break
                except IntegrityError as e:
                    await self.db.rollback()
                    logger.debug(
                        "IntegrityError on creating product, possibly due to slug conflict.",
                        extra={
                            "attempt": attempt,
                            "product_data": data,
                        },
                    )

                    constraint = None
                    orig = getattr(e, "orig", None)
                    diag = getattr(orig, "diag", None) if orig is not None else None
                    if diag is not None:
                        constraint = getattr(diag, "constraint_name", None)
                    if not constraint:
                        msg = str(e).lower()
                        if "slug" in msg and "unique" in msg:
                            constraint = "products_slug_key"

                    if constraint == "products_slug_key" and attempt < max_retries:
                        base = (
                            product.slug.rsplit("-", 1)[0]
                            if "-" in product.slug
                            else product.slug
                        )
                        suffix = uuid.uuid4().hex[:8]
                        product.slug = f"{base}-{suffix}"
                        continue
                    raise

            q = (
                select(Product)
                .where(Product.id == product.id)
                .options(
                    selectinload(Product.variants)
                    .selectinload(ProductVariant.media_associations)
                    .selectinload(ProductMedia.media)
                )
            )
            result = await self.db.execute(q)
            product = result.scalars().one()

            if not getattr(product, "variant_ids", None):
                setattr(product, "variant_ids", [v.id for v in product.variants])

            return product

        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Integrity error while creating product - {str(e)}",
            ) from e
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to create product",
                extra={"payload": payload.model_dump()},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error while creating product - {str(e)}",
            ) from e

    async def update(self, product_id: UUID, payload: ProductUpdate) -> Product:
        q = select(Product).where(Product.id == product_id)
        r = await self.db.execute(q)
        product: Optional[Product] = r.scalars().one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        data = payload.model_dump(exclude_unset=True)
        inline_variants = data.pop("variants", None)
        variant_ids = data.pop("variant_ids", None)
        media_ids = data.pop("media", None)

        new_status = data.get("status", product.status)
        new_is_variable = data.get("is_variable", product.is_variable)
        new_base_price = data.get("base_price", product.base_price)

        if new_status == "active":
            if new_is_variable:
                provided_inline_variants = (
                    inline_variants is not None and len(inline_variants) > 0
                )
                provided_variant_ids = variant_ids is not None and len(variant_ids) > 0

                has_any_variants_after = (
                    provided_inline_variants
                    or provided_variant_ids
                    or await _product_has_variants(self.db, product.id)
                )

                if not has_any_variants_after:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="At least one variant is required for variable products.",
                    )
            else:
                if new_base_price is None:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Base price is required for non-variable products.",
                    )

        try:
            for key, value in data.items():
                if key in ("variants", "variant_ids", "media"):
                    continue
                setattr(product, key, value)

            if variant_ids:
                await _attach_existing_variants(self.db, product, variant_ids)

            if inline_variants:
                normalized = []
                for v in inline_variants:
                    if hasattr(v, "model_dump"):
                        normalized.append(v.model_dump())
                    elif isinstance(v, dict):
                        normalized.append(dict(v))
                    else:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Invalid variant payload",
                        )
                await _create_inline_variants(self.db, product, normalized)

            if media_ids is not None:
                if media_ids == []:
                    await self.db.execute(
                        delete(ProductMedia).where(
                            ProductMedia.product_id == product.id
                        )
                    )
                else:
                    await _validate_media_and_add(self.db, product, media_ids)

            q = select(ProductVariant).where(ProductVariant.product_id == product.id)
            r = await self.db.execute(q)
            all_variants = r.scalars().all()
            if product.status == "active" and product.is_variable:
                missing = [str(v.id) for v in all_variants if v.price is None]
                if missing:
                    raise HTTPException(
                        status_code=400,
                        detail=f"All variants must have price; missing: {', '.join(missing)}",
                    )

            await self.db.flush()
            await self.db.commit()
            await self.db.refresh(product)
            return product

        except IntegrityError as e:
            logger.debug(
                "IntegrityError on updating product",
                extra={"product_id": str(product_id), "payload": payload.model_dump()},
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Integrity error while updating product - {str(e)}",
            ) from e
        except HTTPException:
            await self.db.rollback()
            raise
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to update product",
                extra={"product_id": str(product_id), "payload": payload.model_dump()},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error while updating product - {str(e)}",
            ) from e

    async def delete(self, product_id: UUID) -> None:
        q = select(Product).where(Product.id == product_id)
        r = await self.db.execute(q)
        product: Optional[Product] = r.scalars().one_or_none()

        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
            )

        try:
            await self.db.delete(product)
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Failed to delete product due to DB constraints",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to delete product",
                extra={"product_id": str(product_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete product",
            ) from e
