import sqlalchemy as sa
from typing import Optional
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base
from uuid import UUID
from datetime import datetime

class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
    username: Mapped[str] = mapped_column(sa.String(50), index=True, unique=True, nullable=False)
    email: Mapped[str] = mapped_column(sa.String(255), index=True, unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"))
    is_verified: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    is_admin: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    verification_token: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    verification_token_expiry: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    password_reset_token: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    password_reset_token_expiry: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())

    class Config:
        json_schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "johndoe@example.com",
                "hashed_password": "hashedPassword123!",
                "is_active": True,
                "is_verified": False,
                "verification_token": "someVerificationToken123",
                "verification_token_expiry": "2023-01-02T00:00:00Z",
                "password_reset_token": None,
                "password_reset_token_expiry": None,
                "created_at": "2023-01-01T00:00:00Z",
                "updated_at": "2023-01-01T00:00:00Z"
            }
        }