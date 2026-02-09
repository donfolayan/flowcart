from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.schemas.promo_code import PromoCodeResponse, PromoCodeCreate, PromoCodeUpdate
from app.core.permissions import require_admin
from app.services.promo_code import PromoCodeService

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
    service = PromoCodeService(db)
    promo_code = await service.get(promo_code_id=promo_code_id)
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
    service = PromoCodeService(db)
    promo_codes = await service.list()
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
    service = PromoCodeService(db)
    promo_code = await service.create(payload=payload)
    return PromoCodeResponse.model_validate(promo_code)


@admin_router.post(
    "/{promo_code_id}/activate",
    description="Activate a promo code",
    status_code=status.HTTP_200_OK,
)
async def activate_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
):
    service = PromoCodeService(db)
    return await service.activate(promo_code_id=promo_code_id)


@admin_router.post(
    "/{promo_code_id}/deactivate",
    description="Deactivate a promo code",
    status_code=status.HTTP_200_OK,
)
async def deactivate_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
):
    service = PromoCodeService(db)
    return await service.deactivate(promo_code_id=promo_code_id)


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
    service = PromoCodeService(db)
    promo_code = await service.update(promo_code_id=promo_code_id, payload=payload)
    return PromoCodeResponse.model_validate(promo_code)


@admin_router.delete(
    "/{promo_code_id}",
    description="Delete a promo code",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_promo_code(
    promo_code_id: UUID, db: AsyncSession = Depends(get_session)
):
    service = PromoCodeService(db)
    await service.delete(promo_code_id=promo_code_id)
