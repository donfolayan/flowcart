import sqlalchemy as sa
from uuid import UUID
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums.cart_enums import cart_status, CartStatus
from app.enums.currency_enums import currency_enum, CurrencyEnum

if TYPE_CHECKING:
    from .cart_item import CartItem
    from .order import Order

class Cart(Base):
    __tablename__ = "carts"
    __table_args__ = (
        sa.Index("ux_carts_active_per_user", "user_id", unique=True, postgresql_where=sa.text("status = 'active' AND user_id IS NOT NULL")),
        sa.Index("ux_carts_active_per_session_guest", "session_id", unique=True, postgresql_where=sa.text("status = 'active' AND user_id IS NULL")),
        sa.Index("ix_carts_user_status", "user_id", "status"),
        sa.CheckConstraint("user_id IS NOT NULL OR session_id IS NOT NULL", name="chk_carts_user_or_session")
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")) 
    user_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True) #nullable for guest carts
    session_id: Mapped[str] = mapped_column(sa.String(255), nullable=True, index=True) #for guest carts
    status: Mapped[CartStatus] = mapped_column(cart_status, server_default=sa.text("'active'::cart_status"), nullable=False, index=True)
    currency: Mapped[CurrencyEnum] = mapped_column(currency_enum, server_default=sa.text("'USD'::currency_enum"), nullable=False)
    
    # Totals
    subtotal: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=False, server_default=sa.text("0.00"))
    tax_total: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=False, server_default=sa.text("0.00"))
    discount_total: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=False, server_default=sa.text("0.00"))
    shipping_total: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=False, server_default=sa.text("0.00"))
    total: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), sa.Computed("((subtotal + shipping_total) - discount_total + tax_total)", persisted=True), nullable=False)
    
    # Audit
    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now())
    updated_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now(), onupdate=sa.func.now())
    expires_at: Mapped[Optional[sa.DateTime]] = mapped_column(sa.DateTime(timezone=True), index=True, nullable=True) # for guest carts expiration
    extra_data: Mapped[Optional[dict]] = mapped_column(sa.JSON, nullable=True)
    version: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("1"), nullable=False)
    
    items: Mapped[list["CartItem"]] = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan", lazy="selectin")
    order: Mapped[Optional["Order"]] = relationship("Order", back_populates="cart", uselist=False, lazy="selectin")
    __mapper_args__ = {
        "version_id_col": version
    }
    
    def __repr__(self):
        return f"<Cart(id={self.id}, user_id={self.user_id}, status={self.status}, total={self.total})>"