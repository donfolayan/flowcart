from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status, Response
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from app.schemas.product import ProductResponse, ProductUpdate, ProductCreate
from app.models.product import Product, ProductVariant
from app.models.media import Media
from app.models.product_media import ProductMedia
from app.core.permissions import require_admin

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
) -> List[Product]:
    result = await db.execute(select(Product).offset(skip).limit(limit))
    products = list(result.scalars().all())
    return products


@router.get(
    "/{product_id}",
    summary="Get Product",
    description="Retrieve a single product by its ID.",
    response_model=ProductResponse,
)
async def get_product_by_id(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> Product:
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post(
    "/",
    summary="Create Product",
    description="Create a new product.",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    payload: ProductCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
) -> Product:
    variants_id: List[UUID] = getattr(payload, "variants", []) or []
    media_id: List[UUID] = getattr(payload, "media", []) or []

    # Business logic validations
    if getattr(payload, "status", "draft") == "active":
        if getattr(payload, "is_variable", False) and (not variants_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one variant is required for variable products.",
            )
    if not getattr(payload, "is_variable", False) and not getattr(
        payload, "base_price", None
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Base price is required for non-variable products.",
        )

    try:
        product = Product(**payload.model_dump(exclude={"variants", "media"}))

        db.add(product)
        await db.flush()

        if variants_id:
            query = select(ProductVariant).where(ProductVariant.id.in_(variants_id))
            result = await db.execute(query)
            variants = {v.id: v for v in result.scalars().all()}
            missing_variants = set(variants_id) - set(variants.keys())
            if missing_variants:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Some variants not found: {', '.join(str(v) for v in missing_variants)}",
                )

            conflicting_variants = {
                str(v.id) for v in variants.values() if v.product_id is not None
            }
            if conflicting_variants:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Some variants are already associated with another product and cannot be reused: {', '.join(conflicting_variants)}",
                )

            if product.status == "active":
                bad = [str(v.id) for v in variants.values() if v.price is None]
                if bad:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"All variants must have a price for active products. Missing prices for variants: {', '.join(bad)}",
                    )
            new_variant_status = None
            if product.status == "active":
                new_variant_status = "active"
            else:
                new_variant_status = "draft"

            # Bulk update variants to link to product
            await db.execute(
                update(ProductVariant)
                .where(ProductVariant.id.in_(variants_id))
                .values(product_id=product.id, status=new_variant_status)
            )

        if media_id:
            query = select(Media).where(Media.id.in_(media_id))
            result = await db.execute(query)
            media_items = {m.id: m for m in result.scalars().all()}
            missing_media = set(media_id) - set(media_items.keys())
            if missing_media:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Some media items not found: {', '.join(str(m) for m in missing_media)}",
                )

            # Create ProductMedia associations
            for media in media_items.values():
                association = ProductMedia(
                    product_id=product.id,
                    media_id=media.id,
                )
                db.add(association)
        await db.flush()
        await db.commit()
        await db.refresh(product)
        response.headers["Location"] = f"/products/{product.id}"
        return product

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integrity error while creating product - {str(e)}",
        ) from e

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error while creating product - {str(e)}",
        ) from e


@router.patch(
    "/{product_id}",
    summary="Update Product",
    description="Update an existing product.",
    response_model=ProductResponse,
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_session),
    _admin=Depends(require_admin),
):
    query = select(Product).where(Product.id == product_id)
    result = await db.execute(query)

    product = result.scalars().first()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    update_data = payload.model_dump(exclude_unset=True)

    variants_in_payload = update_data.pop("variants", None)
    media_in_payload = update_data.pop("media", None)

    new_status = update_data.get("status", product.status)
    new_is_variable = update_data.get("is_variable", product.is_variable)
    new_base_price = update_data.get("base_price", product.base_price)

    # if status is active, validate variants and base_price
    if new_status == "active":
        if new_is_variable:
            if variants_in_payload is None:
                query = select(ProductVariant).where(
                    ProductVariant.product_id == product.id
                )
                result = await db.execute(query)
                existing_variant_ids = [v.id for v in result.scalars().all()]

                if not existing_variant_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="At least one variant is required for variable products.",
                    )
            else:
                if not variants_in_payload:
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
        async with db.begin():
            for key, value in update_data.items():
                setattr(product, key, value)

            # if variants are provided, update associations
            if variants_in_payload is not None:
                variants_in_payload = variants_in_payload or []

                if variants_in_payload:
                    query = select(ProductVariant).where(
                        ProductVariant.id.in_(variants_in_payload)
                    )
                    result = await db.execute(query)
                    found_ids = {v.id: v for v in result.scalars().all()}
                    missing_ids = set(variants_in_payload) - set(found_ids.keys())

                    if missing_ids:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Some variants not found: {', '.join(str(v) for v in missing_ids)}",
                        )

                    # prevent variants already linked to other products
                    conflicting_variants = [
                        str(v.id)
                        for v in found_ids.values()
                        if v.product_id not in (None, product.id)
                    ]

                    if conflicting_variants:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Some variants are already associated with another product and cannot be reused: {', '.join(conflicting_variants)}",
                        )

                    if (new_status == "active") and new_is_variable:
                        bad = [str(v.id) for v in found_ids.values() if v.price is None]
                        if bad:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"All variants must have a price for active products. Missing prices for variants: {', '.join(bad)}",
                            )

                    # Disassociate existing variants not in payload
                    q = select(ProductVariant).where(
                        ProductVariant.product_id == product.id
                    )
                    r = await db.execute(q)
                    current_variants = r.scalars().all()
                    to_detach = [
                        v.id
                        for v in current_variants
                        if v.id not in variants_in_payload
                    ]

                    if to_detach:
                        await db.execute(
                            update(ProductVariant)
                            .where(ProductVariant.id.in_(to_detach))
                            .values(product_id=None, status="draft")
                        )

                    # Associate new variants
                    new_variant_status = "active" if new_status == "active" else "draft"
                    await db.execute(
                        update(ProductVariant)
                        .where(ProductVariant.id.in_(variants_in_payload))
                        .values(product_id=product.id, status=new_variant_status)
                    )

            # handle media is provided
            if media_in_payload is not None:
                media_in_payload = media_in_payload or []

                # Remove existing associations not in payload
                q = select(ProductMedia).where(ProductMedia.product_id == product.id)
                r = await db.execute(q)
                found_media = {m.id: m for m in r.scalars().all()}
                missing_media = set(media_in_payload) - set(found_media.keys())

                if missing_media:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Some media items not found: {', '.join(str(m) for m in missing_media)}",
                    )

                # Delete associations not in payload
                query = select(ProductMedia).where(
                    ProductMedia.product_id == product.id
                )
                result = await db.execute(query)
                current_media = {
                    product_media.media_id: product_media
                    for product_media in result.scalars().all()
                }
                to_remove = [
                    mid for mid in current_media.keys() if mid not in found_media.keys()
                ]

                if to_remove:
                    await db.execute(
                        ProductMedia.__table__.delete().where(
                            ProductMedia.product_id == product.id,
                            ProductMedia.media_id.in_(to_remove),
                        )
                    )

                # Add new associations
                to_add = set(media_in_payload) - set(current_media.keys())

                for mid in to_add:
                    db.add(
                        ProductMedia(
                            product_id=product.id,
                            media_id=mid,
                        )
                    )
                else:
                    await db.execute(
                        delete(ProductMedia).where(
                            ProductMedia.product_id == product.id
                        )
                    )

        db.add(product)
        await db.refresh(product)
        return product

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integrity error while updating product - {str(e)}",
        ) from e
