import sqlalchemy as sa 
from uuid import UUID
from datetime import datetime
from slugify import slugify
from decimal import Decimal
from sqlalchemy.dialects.postgresql import UUID as PGUUID, ENUM as PGENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event
from datetime import timezone
from typing import Optional, TYPE_CHECKING

from app.db.base import Base

if TYPE_CHECKING:
    from .media import Media
    from .product_media import ProductMedia
    from .product_variant import ProductVariant
    from .category import Category

PRODUCT_STATUS_ENUM = PGENUM("draft", "active", "archived", name="product_status")

class Product(Base):
    __tablename__ = "products"
    __table_args__ = (sa.CheckConstraint("stock >= 0", name="chk_product_stock_non_negative"),)
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(sa.String(255), index=True, nullable=False)
    slug: Mapped[str] = mapped_column(sa.String(120), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(sa.Text, nullable=True)
    base_price: Mapped[Optional[Decimal]] = mapped_column(sa.Numeric(10, 2, asdecimal=True), nullable=True)
    sku: Mapped[str] = mapped_column(sa.String(50), unique=True, nullable=False)
    is_variable: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    status: Mapped[str] = mapped_column(PRODUCT_STATUS_ENUM, index=True, server_default=sa.text("'draft'::product_status"), nullable=False)
    stock: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text("0"))
    attributes: Mapped[dict] = mapped_column(sa.JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now())
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), index=True, server_default=sa.func.now(), onupdate=sa.func.now())
    is_deleted: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"))
    primary_image_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    primary_image: Mapped["Media | None"] = relationship("Media", lazy="joined", foreign_keys=[primary_image_id])
    
    category: Mapped[Optional["Category"]] = relationship("Category", back_populates="products", lazy="selectin")
    category_id: Mapped[Optional[UUID]] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("categories.id", ondelete="SET NULL", name="fk_products_category_id_categories"), nullable=True, index=True)
    
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
    

@event.listens_for(Product, "before_insert")
def prepare_product(mapper, connection, target):
    """
    - Generate SKU before inserting a new Product, 
    - Ensure base_price for non-variable products,
    - Generate slug from name, make it unique
    """
    if not target.sku:
        from app.util.sku import generate_unique_sku
        target.sku = generate_unique_sku(target.name)
        
    products_table = Product.__table__
    
    stmt = sa.select(sa.func.count()).where(products_table.c.sku == target.sku)
    result = connection.execute(stmt)
    count = result.scalar_one()
    if count > 0:
        from app.util.sku import generate_unique_sku
        target.sku = generate_unique_sku(target.name)
    
    if getattr(target, "status", "draft") == "active" and not getattr(target, "is_variable", False) and getattr(target, "base_price", None) is None:
        raise ValueError("Base price is required for non-variable products.")
    
    base_slug = (getattr(target, "slug", None) or slugify(getattr(target, "name", "") or "")).strip()
    if not base_slug:
        base_slug = f"product-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    slug = base_slug
    
    i = 1
    # query for existence using the connection (synchronous)
    while True:
        stmt = sa.select(sa.func.count()).select_from(products_table).where(products_table.c.slug == slug)
        result = connection.execute(stmt)
        count = result.scalar_one()
        if count == 0:
            break
        # bump and try again
        slug = f"{base_slug}-{i}"
        i += 1

    target.slug = slug

    if target.category_id is None:
        from .category import Category
        default_category = Category.get_default(connection)
        target.category_id = default_category
