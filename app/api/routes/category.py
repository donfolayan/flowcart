from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.category import CategoryResponse, CategoryCreate, CategoryUpdate
from app.core.permissions import require_admin
from app.services.category import CategoryService

admin_router = APIRouter(
    prefix="/admin/categories",
    tags=["Admin Categories"],
    dependencies=[Depends(require_admin)],
)
router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_category(
    category_id: UUID, db: AsyncSession = Depends(get_session)
) -> CategoryResponse:
    service = CategoryService(db)
    category = await service.get(category_id=category_id)
    return CategoryResponse.model_validate(category)


@router.get("/", response_model=List[CategoryResponse], status_code=status.HTTP_200_OK)
async def get_all_categories(
    db: AsyncSession = Depends(get_session),
) -> List[CategoryResponse]:
    service = CategoryService(db)
    categories = await service.list_all()
    return [CategoryResponse.model_validate(category) for category in categories]


@admin_router.post(
    "/",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate, response: Response, db: AsyncSession = Depends(get_session)
) -> CategoryResponse:
    service = CategoryService(db)
    category = await service.create(payload=payload)

    response.headers["Location"] = f"/categories/{category.id}"
    return CategoryResponse.model_validate(category)


@admin_router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
)
async def update_category(
    category_id: UUID, payload: CategoryUpdate, db: AsyncSession = Depends(get_session)
) -> CategoryResponse:
    service = CategoryService(db)
    category = await service.update(category_id=category_id, payload=payload)
    return CategoryResponse.model_validate(category)


@admin_router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_category(
    category_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    service = CategoryService(db)
    await service.delete(category_id=category_id)
