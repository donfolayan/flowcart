import sqlalchemy as sa
from uuid import UUID
from typing import Optional, TYPE_CHECKING, List
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .order import Order


class Address(Base):
    __tablename__ = "addresses"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)

    name: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    company: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    line1: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    line2: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    city: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True, index=True)
    region: Mapped[Optional[str]] = mapped_column(sa.String(120), nullable=True)
    postal_code: Mapped[Optional[str]] = mapped_column(sa.String(30), nullable=True, index=True)
    country: Mapped[Optional[str]] = mapped_column(sa.String(2), nullable=True, index=True)
    phone: Mapped[Optional[str]] = mapped_column(sa.String(50), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)

    extra: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    
    # Relationships
    shipping_orders: Mapped[List["Order"]] = relationship("Order", back_populates="shipping_address", foreign_keys="[Order.shipping_address_id]", lazy="selectin")
    billing_orders: Mapped[List["Order"]] = relationship("Order", back_populates="billing_address", foreign_keys="[Order.billing_address_id]", lazy="selectin")
