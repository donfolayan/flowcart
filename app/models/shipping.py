import sqlalchemy as sa
from uuid import UUID
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums.carrier_enum import CarrierEnum, shipping_carrier
from app.enums.shipping_status_enum import ShippingStatusEnum, shipping_status

if TYPE_CHECKING:
    from .address import Address
    from app.models.order import Order

class Shipping(Base):
    __tablename__ = "shippings"
    __table_args__ = (
        sa.UniqueConstraint("order_id", name="uq_shippings_order_id"),
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True, unique=True)
    address_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("addresses.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # Shipping costs
    shipping_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    shipping_tax_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    
    # Carrier & service
    carrier: Mapped[CarrierEnum] = mapped_column(shipping_carrier, nullable=False)
    
    # Tracking & labels
    tracking_number: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    tracking_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    label_url: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True)
    
    # Timestamps
    status: Mapped[ShippingStatusEnum] = mapped_column(shipping_status, nullable=False, server_default=sa.text("'pending'::shipping_status_enum"))
    shipped_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    
    # Relationships
    order: Mapped["Order"] = relationship("Order", back_populates="shipping", lazy="joined")
    address: Mapped[Optional["Address"]] = relationship("Address", foreign_keys=[address_id], lazy="joined")