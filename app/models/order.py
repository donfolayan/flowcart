import sqlalchemy as sa
from uuid import UUID
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums.order_enums import OrderStatusEnum
from app.enums.currency_enums import CurrencyEnum

if TYPE_CHECKING:
    from .order_item import OrderItem
    from .address import Address
    from .shipping import Shipping
    from .payment import Payment
    from .cart import Cart

class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        sa.CheckConstraint("subtotal_cents >= 0", name="ck_order_subtotal_non_negative"),
        sa.CheckConstraint("tax_cents >= 0", name="ck_order_tax_non_negative"),
        sa.CheckConstraint("discount_cents >= 0", name="ck_order_discount_non_negative"),
        sa.CheckConstraint("total_cents >= 0", name="ck_order_total_non_negative"),
        sa.CheckConstraint("version >= 1", name="ck_order_version_positive"),
        sa.CheckConstraint("discount_cents <= subtotal_cents", name="ck_order_discount_not_exceed_subtotal"),
        sa.Index("ix_orders_idempotency_key_user_id", "idempotency_key", "user_id", unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL")),
        sa.Index("ix_orders_idempotency_key_session_id", "idempotency_key", "session_id", unique=True, postgresql_where=sa.text("idempotency_key IS NOT NULL"))
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    cart_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("carts.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    session_id: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True, index=True)
    currency: Mapped[CurrencyEnum] = mapped_column(sa.Enum(CurrencyEnum, name="currency_enum", create_type=False), server_default=sa.text("'USD'::currency_enum"), nullable=False)
    
    # Totals
    subtotal_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    tax_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    discount_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    total_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))

    # Addresses
    shipping_address_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("addresses.id", ondelete="SET NULL"), index=True, nullable=True)
    billing_address_same_as_shipping: Mapped[bool] = mapped_column(sa.Boolean(), nullable=False, server_default=sa.text("true"))
    billing_address_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("addresses.id", ondelete="SET NULL"), index=True, nullable=True)

    # Immutable snapshots of addresses at time of order
    shipping_address_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    billing_address_snapshot: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    # Audit
    status: Mapped[OrderStatusEnum] = mapped_column(sa.Enum(OrderStatusEnum, name="order_status_enum", create_type=False), server_default=sa.text("'pending'::order_status_enum"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now())
    placed_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    fulfilled_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    canceled_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now(), onupdate=sa.func.now())

    # Idempotency
    idempotency_key: Mapped[Optional[str]] = mapped_column(sa.String(128), nullable=True, unique=False)
    external_reference: Mapped[Optional[str]] = mapped_column(sa.String(255), nullable=True, index=True)

    version: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("1"), nullable=False)

    # Relationships
    cart: Mapped[Optional["Cart"]] = relationship("Cart", back_populates="order", lazy="selectin")
    items: Mapped[List["OrderItem"]] = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    shipping_address: Mapped[Optional["Address"]] = relationship("Address", foreign_keys=[shipping_address_id], back_populates="shipping_orders", lazy="selectin")
    billing_address: Mapped[Optional["Address"]] = relationship("Address", foreign_keys=[billing_address_id], back_populates="billing_orders", lazy="selectin")
    shipping: Mapped[Optional["Shipping"]] = relationship("Shipping", back_populates="order", uselist=False, lazy="selectin")
    payment: Mapped[Optional["Payment"]] = relationship("Payment", back_populates="order", cascade="all, delete-orphan", uselist=False, lazy="selectin")
    
    __mapper_args__ = {"version_id_col": version}
    
    def __repr__(self) -> str:
        return f"<Order id={self.id} user={self.user_id} status={self.status} total={self.total_cents}>"