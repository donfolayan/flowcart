from uuid import UUID
from typing import List
from sqlalchemy import select
from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.models.promo_code import PromoCode
from app.schemas.promo_code import PromoCodeResponse, PromoCodeCreate, PromoCodeUpdate
from app.core.logs.logging_utils import get_logger
from app.core.permissions import require_admin

logger = get_logger("app.promo_code")

router = APIRouter(
    prefix="/promo-codes",
    tags=["Promo Codes"],
)
admin_router = APIRouter(
    prefix="/admin/promo-codes",
    tags=["Promo Codes"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "/{promo_code_id}",
    description="Get promo code by ID",
    response_model=PromoCodeResponse,
    status_code=status.HTTP_200_OK,
)
async def get_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
) -> PromoCodeResponse:
    promo_code = await db.get(PromoCode, promo_code_id)

    if not promo_code:
        logger.info(
            "Promo code not found",
            extra={"promo_code_id": str(promo_code_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
        )

    return PromoCodeResponse.model_validate(promo_code)


@router.get(
    "/",
    description="List all promo codes",
    response_model=List[PromoCodeResponse],
    status_code=status.HTTP_200_OK,
)
async def list_promo_codes(
    db: AsyncSession = Depends(get_session),
) -> List[PromoCodeResponse]:
    result = await db.execute(select(PromoCode))
    promo_codes = result.scalars().all()
    return [PromoCodeResponse.model_validate(pc) for pc in promo_codes]


@admin_router.post(
    "/",
    description="Create a promo code",
    response_model=PromoCodeResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_promo_code(
    payload: PromoCodeCreate, db: AsyncSession = Depends(get_session)
) -> PromoCodeResponse:
    promo_code = PromoCode(**payload.model_dump())
    db.add(promo_code)
    try:
        await db.commit()
        await db.refresh(promo_code)
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error creating promo code: {e}",
            extra={"code": payload.code, "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create promo code",
        )

    return PromoCodeResponse.model_validate(promo_code)


@admin_router.post(
    "/{promo_code_id}/activate",
    description="Activate a promo code",
    status_code=status.HTTP_200_OK,
)
async def activate_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
):
    promo_code = await db.get(PromoCode, promo_code_id)

    if not promo_code:
        logger.info(
            "Promo code not found for activation",
            extra={"promo_code_id": str(promo_code_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
        )

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
    db.add(promo_code)
    try:
        await db.commit()
        await db.refresh(promo_code)
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error activating promo code: {e}",
            extra={"promo_code_id": str(promo_code_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate promo code",
        )

    return {"detail": "Promo code activated successfully"}


@admin_router.post(
    "/{promo_code_id}/deactivate",
    description="Deactivate a promo code",
    status_code=status.HTTP_200_OK,
)
async def deactivate_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
):
    promo_code = await db.get(PromoCode, promo_code_id)

    if not promo_code:
        logger.info(
            "Promo code not found for deactivation",
            extra={"promo_code_id": str(promo_code_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
        )

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
    db.add(promo_code)
    try:
        await db.commit()
        await db.refresh(promo_code)
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error deactivating promo code: {e}",
            extra={"promo_code_id": str(promo_code_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate promo code",
        )

    return {"detail": "Promo code deactivated successfully"}


@admin_router.patch(
    "/{promo_code_id}",
    description="Update a promo code",
    response_model=PromoCodeResponse,
    status_code=status.HTTP_200_OK,
)
async def update_promo_code(
    promo_code_id: UUID,
    payload: PromoCodeUpdate,
    db: AsyncSession = Depends(get_session),
) -> PromoCodeResponse:
    promo_code = await db.get(PromoCode, promo_code_id)

    if not promo_code:
        logger.info(
            "Promo code not found for update",
            extra={"promo_code_id": str(promo_code_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(promo_code, key, value)

    db.add(promo_code)

    try:
        await db.commit()
        await db.refresh(promo_code)
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error updating promo code: {e}",
            extra={"promo_code_id": str(promo_code_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update promo code",
        )

    return PromoCodeResponse.model_validate(promo_code)


@admin_router.delete(
    "/{promo_code_id}",
    description="Delete a promo code",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
):
    promo_code = await db.get(PromoCode, promo_code_id)

    if not promo_code:
        logger.info(
            "Promo code not found for deletion",
            extra={"promo_code_id": str(promo_code_id)},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Promo code not found"
        )

    try:
        await db.delete(promo_code)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error deleting promo code: {e}",
            extra={"promo_code_id": str(promo_code_id), "error": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete promo code",
        )
