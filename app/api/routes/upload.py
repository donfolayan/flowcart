from fastapi import APIRouter, UploadFile, File, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.core.security import get_current_user

router = APIRouter(prefix="/media", tags=["Upload"])


@router.post(
    "/upload",
    dependencies=[Depends(get_current_user)],
    description="Upload a media file to a storage server (Cloudinary) and create media record.",
    status_code=status.HTTP_201_CREATED,
)
async def upload_media(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_session)
):
    pass
