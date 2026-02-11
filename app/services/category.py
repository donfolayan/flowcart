from uuid import UUID
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.logs.logging_utils import get_logger
from app.models.category import Category
from app.schemas.category import CategoryCreate, CategoryUpdate

logger = get_logger("app.category")


class CategoryService:
    """Business logic for category management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, category_id: UUID) -> Category:
        q = (
            select(Category)
            .where(Category.id == category_id)
            .options(
                selectinload(Category.products), selectinload(Category.category_image)
            )
        )
        r = await self.db.execute(q)
        category = r.scalars().one_or_none()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        return category

    async def list_all(self) -> List[Category]:
        q = select(Category).options(
            selectinload(Category.products), selectinload(Category.category_image)
        )
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def create(self, payload: CategoryCreate) -> Category:
        new_category = Category(**payload.model_dump())
        self.db.add(new_category)
        try:
            await self.db.commit()
        except IntegrityError as ie:
            logger.debug(
                "IntegrityError on creating category",
                extra={"payload": payload.model_dump()},
            )
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity Error - {str(ie)}",
            ) from ie
        except Exception as e:
            await self.db.rollback()
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
        r = await self.db.execute(q)
        return r.scalars().one()

    async def update(self, category_id: UUID, payload: CategoryUpdate) -> Category:
        q = select(Category).where(Category.id == category_id)
        r = await self.db.execute(q)
        category = r.scalars().one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(category, key, value)
        try:
            await self.db.commit()
        except IntegrityError as ie:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity Error - {str(ie)}",
            ) from ie
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to update category",
                extra={
                    "category_id": str(category_id),
                    "payload": payload.model_dump(),
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal Server Error - {str(e)}",
            )
        await self.db.refresh(category)
        return category

    async def delete(self, category_id: UUID) -> None:
        q = select(Category).where(Category.id == category_id)
        r = await self.db.execute(q)
        category = r.scalars().one_or_none()
        if not category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Category not found"
            )
        try:
            await self.db.delete(category)
            await self.db.commit()
        except IntegrityError as ie:
            await self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity Error - {str(ie)}",
            ) from ie
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to delete category",
                extra={"category_id": str(category_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal Server Error - {str(e)}",
            )
