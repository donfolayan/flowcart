from typing import List, Optional
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from app.schemas.product import ProductResponse, ProductUpdate, ProductCreate
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_media import ProductMedia
from app.core.permissions import require_admin
from app.schemas.product_variant import ProductVariantCreate
from app.services.product_media import _validate_media_and_add
from app.services.product import (
    _attach_existing_variants,
    _create_inline_variants,
    _product_has_variants,
)

router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


@router.get(
    "/",
    summary="List Products",
    description="Retrieve a list of all products.",
    response_model=List[ProductResponse],
)
async def list_all_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=250),
    db: AsyncSession = Depends(get_session),
) -> List[ProductResponse]:
    result = await db.execute(
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
    products = result.scalars().all()
    return [ProductResponse.model_validate(product) for product in products]


@router.get(
    "/{product_id}",
    summary="Get Product",
    description="Retrieve a single product by its ID.",
    response_model=ProductResponse,
)
async def get_product_by_id(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> ProductResponse:
    q = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.variants)
            .selectinload(ProductVariant.media_associations)
            .selectinload(ProductMedia.media)
        )
    )
    result = await db.execute(q)
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return ProductResponse.model_validate(product)


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
    summary="Create Product",
)
async def create_product(
    payload: ProductCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> ProductResponse:
    data = payload.model_dump(exclude_unset=True)

    inline_variants: Optional[List[ProductVariantCreate]] = data.pop("variants", None)
    variant_ids: Optional[List[UUID]] = data.pop("variant_ids", None)
    media_ids = data.pop("media", None)  # list[UUID] or None

    # Business validations before creating product
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
        db.add(product)
        await db.flush()  # get product.id

        # Attach existing variants (if provided)
        if variant_ids:
            await _attach_existing_variants(db, product, variant_ids)

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
            await _create_inline_variants(db, product, normalized)

        # Validate price rule for active + variable products
        if product.status == "active" and product.is_variable:
            missing = []
            # check existing attached (variant_ids)
            if variant_ids:
                q = select(ProductVariant).where(ProductVariant.id.in_(variant_ids))
                r = await db.execute(q)
                for vv in r.scalars().all():
                    if vv.price is None:
                        missing.append(str(vv.id))
            # check new inline variants
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
                    detail=f"All variants must have a price for active products. Missing prices for: {', '.join(missing)}",
                )

        # Handle media semantics
        if media_ids is not None:
            if media_ids == []:
                # explicit clear
                await db.execute(
                    delete(ProductMedia).where(ProductMedia.product_id == product.id)
                )
            else:
                await _validate_media_and_add(db, product, media_ids)
        MAX_RETRIES = 3
        for attempt in range(MAX_RETRIES + 1):
            try:
                await db.flush()
                await db.commit()
                break
            except IntegrityError as e:
                await db.rollback()

                constraint = None
                orig = getattr(e, "orig", None)
                diag = getattr(orig, "diag", None) if orig is not None else None
                if diag is not None:
                    constraint = getattr(diag, "constraint_name", None)
                if not constraint:
                    # fallback: try to match text (driver-dependent)
                    msg = str(e).lower()
                    if "slug" in msg and "unique" in msg:
                        constraint = "products_slug_key"

                if constraint == "products_slug_key" and attempt < MAX_RETRIES:
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
        result = await db.execute(q)
        product = result.scalars().one()

        if not getattr(product, "variant_ids", None):
            product.variant_ids = [v.id for v in product.variants]

        response.headers["Location"] = f"/products/{product.id}"
        return ProductResponse.model_validate(product)

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integrity error while creating product - {str(e)}",
        ) from e
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while creating product - {str(e)}",
        ) from e


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    dependencies=[Depends(require_admin)],
    summary="Update Product",
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_session),
) -> ProductResponse:
    q = select(Product).where(Product.id == product_id)
    r = await db.execute(q)
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

    # Business validations
    if new_status == "active":
        if new_is_variable:
            # Decide whether the product will have at least one variant after this update.

            provided_inline_variants = (
                inline_variants is not None and len(inline_variants) > 0
            )
            provided_variant_ids = variant_ids is not None and len(variant_ids) > 0

            # If client didn't provide any non-empty variants/variant_ids, check existing variants.
            has_any_variants_after = (
                provided_inline_variants
                or provided_variant_ids
                or await _product_has_variants(db, product.id)
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
        # apply simple attribute changes
        for key, value in data.items():
            # Skip variant/media handling here
            if key in ("variants", "variant_ids", "media"):
                continue
            setattr(product, key, value)

        # variants handling: don't detach existing variants unless client explicitly intended
        if variant_ids:
            # attach existing variant ids (validate inside helper)
            await _attach_existing_variants(db, product, variant_ids)

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
            await _create_inline_variants(db, product, normalized)

        # media handling
        if media_ids is not None:
            if media_ids == []:
                await db.execute(
                    delete(ProductMedia).where(ProductMedia.product_id == product.id)
                )
            else:
                await _validate_media_and_add(db, product, media_ids)

        # Validate price rule for active + variable products
        q = select(ProductVariant).where(ProductVariant.product_id == product.id)
        r = await db.execute(q)
        all_variants = r.scalars().all()
        if product.status == "active" and product.is_variable:
            missing = [str(v.id) for v in all_variants if v.price is None]
            if missing:
                raise HTTPException(
                    status_code=400,
                    detail=f"All variants must have price; missing: {', '.join(missing)}",
                )

        await db.flush()
        await db.commit()
        await db.refresh(product)
        return ProductResponse.model_validate(product)

    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integrity error while updating product - {str(e)}",
        ) from e
    except HTTPException:
        await db.rollback()
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error while updating product - {str(e)}",
        ) from e


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
    summary="Delete Product",
)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_session)):
    q = select(Product).where(Product.id == product_id)
    r = await db.execute(q)
    product: Optional[Product] = r.scalars().one_or_none()

    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Deleting the product will cascade-delete variants if FK is ON DELETE CASCADE in DB
    try:
        await db.delete(product)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Failed to delete product due to DB constraints",
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete product",
        ) from e
