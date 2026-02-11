from fastapi import (
    APIRouter,
    UploadFile,
    File,
    status,
    Depends,
    HTTPException,
    Query,
)
from typing import Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import config
from app.core.permissions import require_admin
from app.db.session import get_session
from app.core.security import get_current_user
from app.core.registry import get_storage_provider
from app.schemas.media import MediaResponse
from app.models.media import Media
from app.core.logs.logging_utils import get_logger

logger = get_logger("app.upload")

FOLDER = config.APPLICATION_FOLDER
STORAGE_PROVIDER = config.STORAGE_PROVIDER

admin_router = APIRouter(
    prefix="/upload",
    tags=["Upload"],
    dependencies=[Depends(require_admin)],
)


@admin_router.post(
    "/upload",
    description="Upload a media file to a storage server and create media record.",
    status_code=status.HTTP_201_CREATED,
)
async def upload_stream(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: Any = Depends(get_current_user),
    folder: Optional[str] = Query(FOLDER, description="Folder to upload the file to"),
) -> MediaResponse:
    provider = get_storage_provider(STORAGE_PROVIDER)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Storage provider is not configured.",
        )

    file_obj = file.file

    try:
        result = await provider.upload_file(
            file=file_obj,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            folder=folder or "",
        )
    except Exception as e:
        logger.exception(
            "File upload failed",
            extra={"filename": file.filename, "user_id": str(current_user.id)},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"File upload failed: {str(e)}",
        ) from e

    file_url = result.get("url")
    public_id = result.get("public_id")
    resource_type = result.get("resource_type", "unknown")
    provider_raw = result.get("raw") or result
    content_type = file.content_type

    size_from_provider = None
    if isinstance(provider_raw, dict):
        size_from_provider = provider_raw.get("bytes")

    media = Media(
        file_url=file_url,
        alt_text=file.filename,
        mime_type=content_type or "application/octet-stream",
        uploaded_by=current_user.id,
        provider=STORAGE_PROVIDER,
        provider_public_id=public_id,
        provider_metadata={
            "resource_type": resource_type,
            "size": size_from_provider,
        },
        is_active=True,
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return MediaResponse.model_validate(media)


@admin_router.delete(
    "/delete/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_media(media_id: str, db: AsyncSession = Depends(get_session)) -> None:
    media = await db.get(Media, media_id)
    if not media:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
        )

    if not media.provider or not media.provider_public_id:
        await db.delete(media)
        await db.commit()
        return

    provider = get_storage_provider(media.provider)
    public_id = media.provider_public_id
    resource_type = (
        media.provider_metadata.get("resource_type")
        if media.provider_metadata
        else "image"
    )

    if provider and public_id:
        try:
            await provider.delete_file(
                public_id=public_id, resource_type=resource_type or "image"
            )
        except Exception as e:
            logger.exception(
                "Failed to delete file from storage provider",
                extra={"media_id": str(media_id), "public_id": public_id},
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to delete file from storage provider: {str(e)}",
            ) from e
    await db.delete(media)
    await db.commit()
    return
