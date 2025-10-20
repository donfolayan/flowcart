import sqlalchemy as sa 
from uuid import UUID
from datetime import datetime
from slugify import slugify
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event

from app.db.base import Base
from app.models.media import Media, ProductMedia
from app.util.sku import generate_unique_sku

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (sa.CheckConstraint("stock >= 0", name="chk_product_stock_non_negative"),)
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(sa.String(100), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=True)
    base_price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=True)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    is_variable: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"))
    stock: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    is_deleted: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    primary_image_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_image: Mapped["Media | None"] = relationship("Media", lazy="joined")
    
    media_associations: Mapped[list["ProductMedia"]] = relationship(
        "ProductMedia", 
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    variants: Mapped[list["ProductVariant"]] = relationship(
        "ProductVariant", 
        back_populates="product",
        cascade="all, delete-orphan", 
        lazy="selectin"
    )

    def __repr__(self):
        return f"<Product(name={self.name}, sku={self.sku})>"
    
# Generate SKU before inserting a new Product, 
# Ensure base_price for non-variable products,
# Generate slug from name
@event.listens_for(Product, "before_insert")
def validate_product(mapper, connection, target):
    if not target.sku:
        target.sku = generate_unique_sku(target.name)
    if not target.is_variable and target.base_price is None:
        raise ValueError("Base price is required for non-variable products.")
    if not target.slug:
        target.slug = slugify(target.name)


class ProductVariant(Base):
    __tablename__ = "product_variants"
    __table_args__ = (
        sa.CheckConstraint("stock >= 0", name="chk_product_variant_stock_non_negative"),
        sa.CheckConstraint("price >= 0", name="chk_product_variant_price_non_negative"),)


    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()'))
    base_product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=False)
    stock: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    primary_image_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_image: Mapped["Media | None"] = relationship("Media", lazy="joined")
    
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    media_associations: Mapped[list["ProductMedia"]] = relationship("ProductMedia", back_populates="variant", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<ProductVariant(name={self.name}, sku={self.sku})>"
    
# Generate SKU before inserting a new ProductVariant
@event.listens_for(ProductVariant, "before_insert")
def generate_variant_sku(mapper, connection, target):
    if not target.sku:
        target.sku = generate_unique_sku(target.name)
        
