import sqlalchemy as sa 
from typing import TYPE_CHECKING
from uuid import UUID
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM as PGENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event

from app.db.base import Base
from app.models.media import Media
from app.models.product_media import ProductMedia
from app.util.sku import generate_unique_sku

if TYPE_CHECKING:
    from app.models.product import Product


VARIANT_STATUS_ENUM = PGENUM("draft", "active", "archived", name="variant_status")

class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        sa.CheckConstraint("stock >= 0", name="chk_product_variant_stock_non_negative"),
        sa.CheckConstraint("price >= 0", name="chk_product_variant_price_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
    product_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="SET NULL"), nullable=True, index=True)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=True)
    stock: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    status: Mapped[str] = mapped_column(VARIANT_STATUS_ENUM, server_default=sa.text("'draft'::variant_status"), nullable=False, index=True)
    primary_image_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_image: Mapped["Media | None"] = relationship("Media", lazy="joined")
    
    product: Mapped["Product | None"] = relationship("Product", back_populates="variants")
    media_associations: Mapped[list["ProductMedia"]] = relationship("ProductMedia", back_populates="variant", cascade="save-update, merge", lazy="selectin")

    def __repr__(self):
        return f"<ProductVariant(name={self.name}, sku={self.sku}, product_id={self.product_id})>"
    
# Generate SKU before inserting a new ProductVariant
@event.listens_for(ProductVariant, "before_insert")
def generate_variant_sku(mapper, connection, target):
    if not target.sku:
        target.sku = generate_unique_sku(target.name)
        
