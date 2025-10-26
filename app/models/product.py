import sqlalchemy as sa 
from uuid import UUID
from datetime import datetime
from slugify import slugify
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM as PGENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event

from app.db.base import Base
from app.models.media import Media
from app.models.product_media import ProductMedia
from app.models.product_variant import ProductVariant
from app.util.sku import generate_unique_sku

PRODUCT_STATUS_ENUM = PGENUM("draft", "active", "archived", name="product_status")

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (sa.CheckConstraint("stock >= 0", name="chk_product_stock_non_negative"),)
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(sa.String(100), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=True)
    base_price: Mapped[Decimal | None] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=True)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    is_variable: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    status: Mapped[str] = mapped_column(PRODUCT_STATUS_ENUM, server_default=sa.text("'draft'::product_status"), nullable=False, index=True)    
    stock: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    is_deleted: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    primary_image_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_image: Mapped["Media | None"] = relationship("Media", lazy="joined")
    
    media_associations: Mapped[list["ProductMedia"]] = relationship(
        "ProductMedia", 
        back_populates="product",
        cascade="save-update, merge",
        lazy="selectin"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", 
        back_populates="product",
        passive_deletes=True, 
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Product(name={self.name}, sku={self.sku}, status={self.status})>"
    
# Generate SKU before inserting a new Product, 
# Ensure base_price for non-variable products,
# Generate slug from name
@event.listens_for(Product, "before_insert")
def prepare_product(mapper, connection, target):
    if not target.sku:
        target.sku = generate_unique_sku(target.name)
    if getattr(target, "status", "draft") == "active" and not getattr(target, "is_variable", False) and getattr(target, "base_price", None) is None:
        raise ValueError("Base price is required for non-variable products.")
    if not getattr(target, "slug", None):
        target.slug = slugify(target.name)
