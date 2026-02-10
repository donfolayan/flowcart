from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_admin
from app.db.session import get_session
from app.schemas.media import MediaResponse, MediaCreate
from app.services.media import MediaService

admin_router = APIRouter(
    prefix="/admin/media",
    tags=["Admin Media"],
    dependencies=[Depends(require_admin)],
)
router = APIRouter(
    prefix="/media",
    tags=["Media"],
)


@router.get(
    "/{media_id}",
    description="Get media by ID",
    response_model=MediaResponse,
    status_code=status.HTTP_200_OK,
)
async def get_media(
    media_id: UUID, db: AsyncSession = Depends(get_session)
) -> MediaResponse:
    service = MediaService(db)
    media = await service.get(media_id=media_id)
    return MediaResponse.model_validate(media)


@router.get("/", description="List all media", response_model=List[MediaResponse])
async def list_media(db: AsyncSession = Depends(get_session)) -> List[MediaResponse]:
    service = MediaService(db)
    media_items = await service.list()
    return [MediaResponse.model_validate(item) for item in media_items]


@admin_router.post(
    "/",
    description="Create new media",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_media(
    payload: MediaCreate, response: Response, db: AsyncSession = Depends(get_session)
) -> MediaResponse:
    service = MediaService(db)
    new_media = await service.create(payload=payload)

    response.headers["Location"] = f"/media/{new_media.id}"
    return MediaResponse.model_validate(new_media)
