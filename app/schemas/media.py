from pydantic import BaseModel, Field, ConfigDict
from uuid import UUID
from datetime import datetime


class MediaBase(BaseModel):
    file_url: str = Field(..., description="URL of the media file")
    alt_text: str | None = Field(None, description="Alternative text for the media")
    mime_type: str = Field(..., description="MIME type of the media file")
    uploaded_by: UUID = Field(..., description="ID of the user who uploaded the media")


class MediaCreate(MediaBase):
    pass


class MediaResponse(MediaBase):
    id: UUID = Field(..., description="Unique identifier of the media")
    uploaded_at: datetime = Field(
        ..., description="Timestamp when the media was uploaded"
    )
    model_config = ConfigDict(from_attributes=True)
