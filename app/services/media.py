from uuid import UUID
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logs.logging_utils import get_logger
from app.models.media import Media
from app.schemas.media import MediaCreate

logger = get_logger("app.media")


class MediaService:
    """Business logic for media management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, media_id: UUID) -> Media:
        q = select(Media).where(Media.id == media_id)
        r = await self.db.execute(q)
        media: Optional[Media] = r.scalars().one_or_none()

        if not media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
            )

        return media

    async def list(self) -> List[Media]:
        q = select(Media).order_by(Media.uploaded_at.desc())
        r = await self.db.execute(q)
        return list(r.scalars().all())

    async def create(self, payload: MediaCreate) -> Media:
        payload_data = payload.model_dump()

        if not payload_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid media data - empty payload",
            )

        new_media = Media(**payload_data)

        try:
            self.db.add(new_media)
            await self.db.commit()
            await self.db.refresh(new_media)
        except IntegrityError as e:
            await self.db.rollback()
            logger.debug(
                "IntegrityError on creating media",
                extra={"payload": payload_data},
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Media creation failed - integrity error - {str(e)}",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to create media",
                extra={"payload": payload_data},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Media creation failed - unexpected error - {str(e)}",
            ) from e

        return new_media
