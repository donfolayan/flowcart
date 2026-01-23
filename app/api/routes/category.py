from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.category import Category
from app.schemas.category import CategoryResponse, CategoryCreate, CategoryUpdate
from app.core.permissions import require_admin
from app.core.logging_utils import get_logger

logger = get_logger("app.category")

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post(
    "/",
    response_model=CategoryResponse,
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_201_CREATED,
)
async def create_category(
    payload: CategoryCreate, response: Response, db: AsyncSession = Depends(get_session)
) -> CategoryResponse:
    new_category = Category(**payload.model_dump())
    db.add(new_category)
    try:
        await db.commit()
    except IntegrityError as ie:
        logger.debug(
            "IntegrityError on creating category",
            extra={"payload": payload.model_dump()},
        )
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity Error - {str(ie)}",
        ) from ie
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Failed to create category",
            extra={"payload": payload.model_dump()},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        )

    q = (
        select(Category)
        .where(Category.id == new_category.id)
        .options(
            selectinload(Category.products),
            selectinload(Category.category_image),
        )
    )
    r = await db.execute(q)
    category_with_rels = r.scalars().one()

    response.headers["Location"] = f"/categories/{category_with_rels.id}"
    return CategoryResponse.model_validate(category_with_rels)


@router.get(
    "/{category_id}",
    response_model=CategoryResponse,
    status_code=status.HTTP_200_OK,
)
async def get_category(
    category_id: UUID, db: AsyncSession = Depends(get_session)
) -> CategoryResponse:
    q = (
        select(Category)
        .where(Category.id == category_id)
        .options(selectinload(Category.products), selectinload(Category.category_image))
    )
    r = await db.execute(q)
    category = r.scalars().one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return CategoryResponse.model_validate(category)


@router.get("/", response_model=List[CategoryResponse], status_code=status.HTTP_200_OK)
async def get_all_categories(
    db: AsyncSession = Depends(get_session),
) -> List[CategoryResponse]:
    q = select(Category).options(
        selectinload(Category.products), selectinload(Category.category_image)
    )
    r = await db.execute(q)
    categories = r.scalars().all()
    return [CategoryResponse.model_validate(category) for category in categories]


@router.patch(
    "/{category_id}",
    response_model=CategoryResponse,
    dependencies=[Depends(require_admin)],
    status_code=status.HTTP_200_OK,
)
async def update_category(
    category_id: UUID, payload: CategoryUpdate, db: AsyncSession = Depends(get_session)
) -> CategoryResponse:
    q = select(Category).where(Category.id == category_id)
    r = await db.execute(q)
    category = r.scalars().one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, key, value)
    try:
        await db.commit()
    except IntegrityError as ie:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity Error - {str(ie)}",
        ) from ie
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Failed to update category",
            extra={"category_id": str(category_id), "payload": payload.model_dump()},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        )
    await db.refresh(category)
    return CategoryResponse.model_validate(category)


@router.delete(
    "/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
async def delete_category(
    category_id: UUID, db: AsyncSession = Depends(get_session)
) -> None:
    q = select(Category).where(Category.id == category_id)
    r = await db.execute(q)
    category = r.scalars().one_or_none()
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
        )
    try:
        await db.delete(category)
        await db.commit()
    except ValueError as ve:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete default category - {str(ve)}",
        ) from ve
    except IntegrityError as ie:
        await db.rollback()
        logger.debug(
            "IntegrityError on deleting category",
            extra={"category_id": str(category_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity Error - {str(ie)}",
        ) from ie
    except Exception as e:
        await db.rollback()
        logger.exception(
            "Failed to delete category",
            extra={"category_id": str(category_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        )
    return None
