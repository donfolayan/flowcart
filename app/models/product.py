import sqlalchemy as sa 
from uuid import UUID, uuid4
from datetime import datetime
from slugify import slugify
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event

from app.db.base import Base
from app.util.sku import generate_unique_sku

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        sa.Index("ix_product_name", "name"),
        sa.Index("ix_product_sku", "sku"),
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(sa.String(100), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=True)
    base_price: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=True)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    is_variable: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    is_active: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("true"))
    stock: Mapped[int] = mapped_column(sa.Integer, nullable=False, default=0)
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now())
    is_deleted: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    
    images: Mapped[list["ProductImage"]] = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    variants: Mapped[list["ProductVariant"]] = relationship("ProductVariant", back_populates="product", cascade="all, delete-orphan")

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
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(sa.String(100), nullable=False)
    price: Mapped[float] = mapped_column(sa.Numeric(10, 2), nullable=False)
    stock: Mapped[int] = mapped_column(sa.Integer, server_default=sa.text("0"))
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    image_url: Mapped[str] = mapped_column(sa.String(255), nullable=True)
    
    product: Mapped["Product"] = relationship("Product", back_populates="variants")
    images: Mapped[list["ProductImage"]] = relationship("ProductImage", back_populates="variant", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<ProductVariant(name={self.name}, sku={self.sku})>"
    
# Generate SKU before inserting a new ProductVariant
@event.listens_for(ProductVariant, "before_insert")
def generate_variant_sku(mapper, connection, target):
    if not target.sku:
        target.sku = generate_unique_sku(target.name)
        
        
class ProductImage(Base):
    __tablename__ = "product_images"
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("products.id"), nullable=False)
    variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("product_variants.id"), nullable=True)
    image_url: Mapped[str] = mapped_column(sa.String(255), nullable=True)
    alt_text: Mapped[str] = mapped_column(sa.String(150), nullable=True)
    is_variant_image: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))

    product: Mapped["Product"] = relationship("Product", back_populates="images")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="images")