import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from uuid import UUID
from datetime import datetime

class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
    stripe_event_id: Mapped[str] = mapped_column(sa.String(255), unique=True, nullable=False)
    event_type: Mapped[str] = mapped_column(sa.String(100), index=True, nullable=False)
    received_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    processed: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    processed_at: Mapped[datetime | None] = mapped_column(sa.DateTime(timezone=True), nullable=True)

    class Config:
        json_schema_extra = {
            "example": {
                "event_type": "payment_intent.succeeded",
                "received_at": "2023-01-01T00:00:00Z",
                "processed": False,
                "processed_at": None
            }
        }