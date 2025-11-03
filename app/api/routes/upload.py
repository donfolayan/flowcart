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
from decouple import config
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.security import get_current_user
from app.core.storage.registry import get_provider
from app.core.storage.cloudinary_provider import CloudinaryProvider
from app.schemas.media import MediaResponse
from app.models.media import Media

FOLDER = config("APPLICATION_FOLDER", cast=str)

router = APIRouter(prefix="/media", tags=["Upload"])


@router.post(
    "/upload",
    description="Upload a media file to a storage server (Cloudinary) and create media record.",
    status_code=status.HTTP_201_CREATED,
)
async def upload_stream(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session),
    current_user: Any = Depends(get_current_user),
    folder: Optional[str] = Query(
        None, description="Cloudinary folder to upload the file to"
    ),
) -> MediaResponse:
    provider = get_provider("cloudinary")
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
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"File upload failed: {str(e)}",
        ) from e

    file_url = result.get("secure_url") or result.get("url")
    public_id = result.get("public_id")
    resource_type = result.get("resource_type", "unknown")
    provider_raw = result or result.get("raw")

    size_from_provider = None
    if isinstance(provider_raw, dict):
        size_from_provider = provider_raw.get("bytes")

    media = Media(
        file_url=file_url,
        alt_text=file.filename,
        mime_type=resource_type,
        uploaded_by=current_user.id,
        provider=CloudinaryProvider.name,
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
