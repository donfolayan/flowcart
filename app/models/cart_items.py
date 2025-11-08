import sqlalchemy as sa
from uuid import UUID
from decimal import Decimal
from typing import Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.enums.currency_enums import CurrencyEnum

if TYPE_CHECKING:
    from .cart import Cart

class CartItem(Base):
    __tablename__ = "cart_items"
    __table_args__ = (
        sa.Index("ix_cart_items_cart_product", "cart_id", "product_id"),
        sa.CheckConstraint("quantity > 0", name="chk_cart_item_quantity_positive"),
        sa.UniqueConstraint("cart_id", "product_id", "variant_id", name="uq_cart_item_cart_product_variant"),
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    cart_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("carts.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Product details
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False, index=True)
    variant_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(sa.String(255), nullable=False, index=True)
    product_snapshot: Mapped[dict] = mapped_column(sa.JSON, nullable=False)
    
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))

    # Pricing details
    unit_price_currency: Mapped[CurrencyEnum] = mapped_column(sa.Enum(CurrencyEnum, name="currency_enum"), server_default=sa.text("'USD'::currency_enum"), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2, asdecimal=True), nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2, asdecimal=True), nullable=False)
    discount_amount: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2, asdecimal=True), nullable=False)
    line_total: Mapped[Decimal] = mapped_column(sa.Numeric(12, 2, asdecimal=True), sa.Computed("((unit_price * quantity) - discount_amount + tax_amount)", persisted=True),nullable=False)

    # Audit
    created_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now())
    updated_at: Mapped[sa.DateTime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now(), onupdate=sa.func.now())
    
    cart: Mapped["Cart"] = relationship("Cart", back_populates="items")
    
    def __repr__(self):
        return f"<CartItem(product_id={self.product_id}, quantity={self.quantity}, unit_price={self.unit_price}, line_total={self.line_total})>"