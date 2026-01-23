from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime


class WebhookEventBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_type: str = Field(..., description="Type of the webhook event")
    payload: dict = Field(..., description="Payload of the webhook event")
    received_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Timestamp when the webhook event was received",
    )


class WebhookEventCreate(WebhookEventBase):
    pass


class WebhookEventResponse(WebhookEventBase):
    id: UUID = Field(..., description="Unique identifier of the webhook event")
    processed: bool = Field(
        False, description="Indicates if the webhook event has been processed"
    )
    processed_at: Optional[datetime] = Field(
        None, description="Timestamp when the webhook event was processed"
    )
    created_at: datetime = Field(..., description="Creation timestamp of the webhook event")
    updated_at: datetime = Field(..., description="Last update timestamp of the webhook event")