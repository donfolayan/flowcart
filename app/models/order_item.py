import sqlalchemy as sa
from uuid import UUID
from typing import Optional, TYPE_CHECKING
from datetime import datetime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from .order import Order
    
class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (
        sa.CheckConstraint("quantity > 0", name="ck_orderitem_quantity_positive"),
        sa.CheckConstraint("unit_price_cents >= 0", name="ck_orderitem_unit_price_non_negative"),
        sa.CheckConstraint("line_total_cents >= 0", name="ck_orderitem_line_total_non_negative"),
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    order_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False, index=True)
    variant_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    sku: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    unit_price_cents: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    quantity: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("1"))
    line_total_cents: Mapped[int] = mapped_column(sa.Integer, sa.Computed("quantity * unit_price_cents", persisted=True), nullable=False)
    
    #relationship
    order: Mapped["Order"] = relationship("Order", back_populates="items", lazy="joined")
    
    # Audit fields
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)