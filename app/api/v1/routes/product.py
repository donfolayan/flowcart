from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status, Response
from app.db.session import get_session
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.product import ProductResponse, ProductUpdate, ProductCreate
from app.core.permissions import require_admin
from app.core.logs.logging_utils import get_logger
from app.services.product import ProductService

logger = get_logger("app.product")
admin_router = APIRouter(
    prefix="/admin/products",
    tags=["Admin Products"],
    dependencies=[Depends(require_admin)],
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
    service = ProductService(db)
    products = await service.list(skip=skip, limit=limit)
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
    service = ProductService(db)
    product = await service.get(product_id=product_id)
    return ProductResponse.model_validate(product)


@admin_router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Product",
)
async def create_product(
    payload: ProductCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
) -> ProductResponse:
    service = ProductService(db)
    product = await service.create(payload=payload)
    response.headers["Location"] = f"/products/{product.id}"
    return ProductResponse.model_validate(product)


@admin_router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update Product",
)
async def update_product(
    product_id: UUID,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_session),
) -> ProductResponse:
    service = ProductService(db)
    product = await service.update(product_id=product_id, payload=payload)
    return ProductResponse.model_validate(product)


@admin_router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Product",
)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_session)):
    service = ProductService(db)
    await service.delete(product_id=product_id)
