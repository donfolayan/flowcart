import sqlalchemy as sa
from uuid import UUID
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .user import User


class RefreshToken(Base):
    """
    Stores refresh tokens in the database for secure token management.
    
    Each record represents one device/session for a user.
    Tokens can be revoked individually (logout) or all at once (logout-all).
    """
    __tablename__ = "refresh_tokens"
    
    id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        primary_key=True, 
        server_default=sa.text("gen_random_uuid()")
    )
    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), 
        sa.ForeignKey("users.id", ondelete="CASCADE"), 
        nullable=False,
        index=True
    )
    token_hash: Mapped[str] = mapped_column(
        sa.String(255), 
        nullable=False, 
        unique=True
    )
    device_id: Mapped[Optional[str]] = mapped_column(
        sa.String(255), 
        nullable=True
    )
    is_revoked: Mapped[bool] = mapped_column(
        sa.Boolean, 
        nullable=False, 
        server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), 
        server_default=sa.func.now(), 
        nullable=False,
        index=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), 
        nullable=False,
        index=True
    )
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True), 
        nullable=True,
        index=True
    )
    
    # Relationship to user
    user: Mapped["User"] = relationship("User", back_populates="refresh_tokens")
    
    def __repr__(self):
        return f"<RefreshToken(id={self.id}, user_id={self.user_id}, is_revoked={self.is_revoked})>"
    
    def is_valid(self) -> bool:
        """Check if token is valid (not revoked and not expired)."""
        from datetime import timezone as tz
        now = datetime.now(tz.utc)
        return not self.is_revoked and self.expires_at > now
