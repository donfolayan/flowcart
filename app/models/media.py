import sqlalchemy as sa
from uuid import UUID
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product_media import ProductMedia

class Media(Base):
    __tablename__ = "media"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    file_url: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    alt_text: Mapped[str] = mapped_column(sa.String(150), nullable=True)
    mime_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), index=True)
    uploaded_by: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider: Mapped[str | None] = mapped_column(sa.String(100), nullable=True, index=True)
    provider_public_id: Mapped[str | None] = mapped_column(sa.String(200), nullable=True, index=True)
    provider_metadata: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"), index=True, nullable=False)
    
    product_associations: Mapped[list["ProductMedia"]] = relationship("ProductMedia", back_populates="media", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Media(id={self.id}, file_url={self.file_url}, alt_text={self.alt_text}, mime_type={self.mime_type}, uploaded_at={self.uploaded_at}, uploaded_by={self.uploaded_by})>"
    