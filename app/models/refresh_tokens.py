import sqlalchemy as sa
from uuid import UUID
from app.db.base import Base
from typing import Optional
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PGUUID

class RefreshTokens(Base):
    __tablename__ = "refresh_tokens"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash: Mapped[str] = mapped_column(sa.String(255), nullable=False, unique=True)
    device_id: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    is_revoked: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.text("false"))
    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now())
    expires_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=False)
    last_used_at: Mapped[Optional[sa.DateTime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)