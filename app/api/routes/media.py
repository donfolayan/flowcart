from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import require_admin
from app.db.session import get_session
from app.models.media import Media
from app.schemas.media import MediaResponse, MediaCreate

router = APIRouter(
    prefix="/media",
    tags=["media"],
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
    q = select(Media).where(Media.id == media_id)
    r = await db.execute(q)
    media: Optional[Media] = r.scalars().one_or_none()

    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    return media


@router.post(
    "/",
    description="Create new media",
    response_model=MediaResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
async def create_media(
    payload: MediaCreate, response: Response, db: AsyncSession = Depends(get_session)
) -> MediaResponse:
    # Check payload data
    payload_data = payload.model_dump()

    if not payload_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid media data - empty payload",
        )

    # Create new media instance
    new_media = Media(**payload_data)

    # Attempt to add and commit new media to the database
    try:
        db.add(new_media)
        await db.commit()
        await db.refresh(new_media)
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Media creation failed - integrity error - {str(e)}",
        ) from e
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Media creation failed - unexpected error - {str(e)}",
        ) from e

    response.headers["Location"] = f"/media/{new_media.id}"
    return new_media
