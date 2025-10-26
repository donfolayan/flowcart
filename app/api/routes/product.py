from typing import List, Optional
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
    dependencies=[Depends(require_admin)],
)
async def create_product(
    payload: ProductCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
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
    dependencies=[Depends(require_admin)],
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_session),
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
        for key, value in update_data.items():
            setattr(product, key, value)

        if variants_in_payload == [] and new_is_variable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one variant is required for variable products.",
            )

        # if variants are provided, update associations
        if variants_in_payload is not None:
            variants_in_payload = variants_in_payload or []

            # create buckets for existing, to add, to remove
            existing_ids: List[UUID] = []
            update_items: List[dict] = []
            create_items: List[dict] = []

            # normalize input: accept UUIDs (or str), dicts, or pydantic-like objects
            for v in variants_in_payload:
                if isinstance(v, (str, UUID)):
                    existing_ids.append(UUID(str(v)))
                    continue

                # Handle Pydantic models or plain dicts
                if hasattr(v, "model_dump"):
                    d = v.model_dump()
                elif isinstance(v, dict):
                    d = dict(v)
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Invalid variant data provided.",
                    )

                vid = d.get("id")
                if vid:
                    d["id"] = UUID(str(vid))
                    existing_ids.append(d["id"])
                    update_items.append(d)
                else:
                    create_items.append(d)

            # Fetch existing variants (if any)
            found_existing = {}
            if existing_ids:
                q = select(ProductVariant).where(ProductVariant.id.in_(existing_ids))
                r = await db.execute(q)

                for var in r.scalars().all():
                    found_existing[var.id] = var

                missing_ids = set(existing_ids) - set(found_existing.keys())
                if missing_ids:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Some variants not found: {', '.join(str(v) for v in missing_ids)}",
                    )

                # prevent variants already linked to other products
                conflicting_variants = [
                    str(v.id)
                    for v in found_existing.values()
                    if v.product_id not in (None, product.id)
                ]

                if conflicting_variants:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Some variants are already associated with another product and cannot be reused: {', '.join(conflicting_variants)}",
                    )

            # Validate prices if needed
            if (new_status == "active") and new_is_variable:
                bad_existing = [
                    str(vv.id) for vv in found_existing.values() if vv.price is None
                ]
                bad_new = [
                    f"(new index {i})"
                    for i, nv in enumerate(create_items)
                    if nv.get("price") is None
                ]
                bad = bad_existing + bad_new
                if bad:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"All variants must have a price for active products. Missing prices for: {', '.join(bad)}",
                    )

            # Apply updates to existing variants
            for item in update_items:
                vid = item["id"]
                variant = found_existing.get(vid)

                if not variant:
                    continue

                # Update only provided fields
                for key, value in item.items():
                    if key == "id":
                        continue
                    setattr(variant, key, value)

                # Ensure association if currently assigned
                if variant.product_id is None:
                    variant.product_id = product.id

                # Ensure correct status
                variant.status = "active" if new_status == "active" else variant.status
                db.add(variant)

            # Create new variants and associate
            for nv in create_items:
                create_data = {k: v for k, v in nv.items() if k != "id"}
                create_data.setdefault("product_id", product.id)
                create_data.setdefault(
                    "status", "active" if new_status == "active" else "draft"
                )
                new_variant = ProductVariant(**create_data)
                db.add(new_variant)

        # Media

        if media_in_payload == []:
            # clear all associations
            await db.execute(
                delete(ProductMedia).where(ProductMedia.product_id == product.id)
            )

        else:
            if media_in_payload:
                # validate Media rows exist
                q = select(Media).where(Media.id.in_(media_in_payload))
                r = await db.execute(q)

                found_media = {m.id: m for m in r.scalars().all()}
                missing_media = set(media_in_payload) - set(found_media.keys())

                if missing_media:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Some media items not found: {', '.join(str(m) for m in missing_media)}",
                    )

                # Current associations (media_ids)
                q = select(ProductMedia).where(ProductMedia.product_id == product.id)
                r = await db.execute(q)

                current_media = {pm.media_id: pm for pm in r.scalars().all()}

                # Add only new associations
                to_add = set(media_in_payload) - set(current_media.keys())

                for mid in to_add:
                    db.add(ProductMedia(product_id=product.id, media_id=mid))

        await db.flush()
        await db.refresh(product)
        return product

    except IntegrityError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Integrity error while updating product - {str(e)}",
        ) from e


@router.delete(
    "/{product_id}",
    summary="Delete Product",
    description="Delete a product by its ID.",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_product(
    product_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    # Check if the product exists
    product_query = select(Product).where(Product.id == product_id)
    product_result = await db.execute(product_query)
    product: Optional[Product] = product_result.scalars().one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    # Delete the product
    await db.delete(product)
    await db.commit()
    return None
