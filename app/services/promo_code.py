from uuid import UUID
from typing import List

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logs.logging_utils import get_logger
from app.models.promo_code import PromoCode
from app.schemas.promo_code import PromoCodeCreate, PromoCodeUpdate

logger = get_logger("app.promo_code")


class PromoCodeService:
    """Business logic for promo code management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, promo_code_id: UUID) -> PromoCode:
        promo_code = await self.db.get(PromoCode, promo_code_id)

        if not promo_code:
            logger.info(
                "Promo code not found",
                extra={"promo_code_id": str(promo_code_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
            )

        return promo_code

    async def list(self) -> List[PromoCode]:
        result = await self.db.execute(select(PromoCode))
        return list(result.scalars().all())

    async def create(self, payload: PromoCodeCreate) -> PromoCode:
        promo_code = PromoCode(**payload.model_dump())
        self.db.add(promo_code)
        try:
            await self.db.commit()
            await self.db.refresh(promo_code)
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error creating promo code: {e}",
                extra={"code": payload.code, "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create promo code",
            )

        return promo_code

    async def activate(self, promo_code_id: UUID) -> dict:
        promo_code = await self.get(promo_code_id)

        if promo_code.is_active:
            logger.info(
                "Promo code already active",
                extra={"promo_code_id": str(promo_code_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Promo code is already active",
            )

        promo_code.is_active = True
        self.db.add(promo_code)
        try:
            await self.db.commit()
            await self.db.refresh(promo_code)
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error activating promo code: {e}",
                extra={"promo_code_id": str(promo_code_id), "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to activate promo code",
            )

        return {"detail": "Promo code activated successfully"}

    async def deactivate(self, promo_code_id: UUID) -> dict:
        promo_code = await self.get(promo_code_id)

        if not promo_code.is_active:
            logger.info(
                "Promo code already inactive",
                extra={"promo_code_id": str(promo_code_id)},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Promo code is already inactive",
            )

        promo_code.is_active = False
        self.db.add(promo_code)
        try:
            await self.db.commit()
            await self.db.refresh(promo_code)
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error deactivating promo code: {e}",
                extra={"promo_code_id": str(promo_code_id), "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to deactivate promo code",
            )

        return {"detail": "Promo code deactivated successfully"}

    async def update(self, promo_code_id: UUID, payload: PromoCodeUpdate) -> PromoCode:
        promo_code = await self.get(promo_code_id)

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(promo_code, key, value)

        self.db.add(promo_code)

        try:
            await self.db.commit()
            await self.db.refresh(promo_code)
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error updating promo code: {e}",
                extra={"promo_code_id": str(promo_code_id), "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update promo code",
            )

        return promo_code

    async def delete(self, promo_code_id: UUID) -> None:
        promo_code = await self.get(promo_code_id)

        try:
            await self.db.delete(promo_code)
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(
                f"Error deleting promo code: {e}",
                extra={"promo_code_id": str(promo_code_id), "error": str(e)},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete promo code",
            )
