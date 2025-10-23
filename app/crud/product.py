from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from app.schemas.product import ProductResponse, ProductCreateNested
from app.schemas.media import ProductMediaRef
from app.models.product import Product, ProductVariant
from app.models.media import Media, ProductMedia
from app.core.dependencies import require_admin

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
)
async def create_product(
    payload: ProductCreateNested,
    db: AsyncSession = Depends(get_session),
    admin_user=Depends(require_admin),
) -> Product:
    product_data = payload.model_dump(exclude={"variants", "media"})
    product = Product(**product_data)

    for variant in payload.variants or []:
        variant_data = ProductVariant(**variant.model_dump())
        product.variants.append(variant_data)

    media_ref: List[ProductMediaRef] = payload.media or []
    media_ids = [media.media_id for media in media_ref]
    if media_ids:
        query = select(Media).where(Media.id.in_(media_ids))
        result = await db.execute(query)
        found_ids = {row[0] for row in result.all()}
        missing_ids = set(media_ids) - found_ids
        if missing_ids:
            raise HTTPException(
                status_code=400, detail=f"Media IDs not found: {missing_ids}"
            )

    for i, media in enumerate(media_ref):
        product_media = ProductMedia(
            media_id=media.media_id, order=i, is_primary=media.is_primary
        )
        product.media_associations.append(product_media)

    try:
        async with db.begin():
            db.add(product)
            await db.flush()
        await db.refresh(product)
        return product
    except IntegrityError as e:
        raise HTTPException(
            status_code=400, detail="Integrity error while creating product"
        ) from e
    except ValueError as e:
        raise HTTPException(
            status_code=400, detail=f"Invalid data provided - {str(e)}"
        ) from e
