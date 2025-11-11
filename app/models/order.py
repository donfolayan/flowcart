import sqlalchemy as sa
from uuid import UUID
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums.order_enums import OrderStatusEnum
from app.enums.currency_enums import CurrencyEnum

if TYPE_CHECKING:
    from .order_item import OrderItem

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        sa.CheckConstraint("subtotal_cents >= 0", name="ck_order_subtotal_non_negative"),
        sa.CheckConstraint("tax_cents >= 0", name="ck_order_tax_non_negative"),
        sa.CheckConstraint("discount_cents >= 0", name="ck_order_discount_non_negative"),
        sa.CheckConstraint("shipping_cents >= 0", name="ck_order_shipping_non_negative"),
        sa.CheckConstraint("total_cents >= 0", name="ck_order_total_non_negative"),
        sa.CheckConstraint("version >= 1", name="ck_order_version_positive")
    )
        
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    cart_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("carts.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    currency: Mapped[CurrencyEnum] = mapped_column(sa.Enum(CurrencyEnum, name="currency_enum", create_type=False), server_default=sa.text("'USD'::currency_enum"), nullable=False)
    
    # Totals
    subtotal_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    tax_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    discount_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    shipping_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    total_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False)

    # Addresses
    shipping_address: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    billing_address: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    
    # Payment
    payment_provider: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True)
    payment_provider_id: Mapped[Optional[str]] = mapped_column(sa.String(100), nullable=True, index=True)
    
    extra_data: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    
    # Audit
    status: Mapped[OrderStatusEnum] = mapped_column(sa.Enum(OrderStatusEnum, name="order_status_enum", create_type=False), server_default=sa.text("'pending'::order_status_enum"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now())
    placed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now(), onupdate=sa.func.now())
    
    version: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("1"), nullable=False)
    
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    
    __mapper_args__ = {"version_id_col": version}