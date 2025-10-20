import sqlalchemy as sa
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.product import Product, ProductVariant

class Media(Base):
    __tablename__ = "media"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    file_url: Mapped[str] = mapped_column(sa.String(255), nullable=False)
    alt_text: Mapped[str] = mapped_column(sa.String(150), nullable=True)
    mime_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), index=True)
    uploaded_by: Mapped[PGUUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    
    product_associations: Mapped[list["ProductMedia"]] = relationship("ProductMedia", back_populates="media", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Media(id={self.id}, file_url={self.file_url}, alt_text={self.alt_text}, mime_type={self.mime_type}, uploaded_at={self.uploaded_at}, uploaded_by={self.uploaded_by})>"
    

class ProductMedia(Base):
    __tablename__ = "product_media"
    __table_args__ = (
        sa.UniqueConstraint("product_id", "media_id", "variant_id", name="uix_product_media_unique"),
        sa.UniqueConstraint("product_id", "is_primary", name="uix_product_primary_image", deferrable=True, initially="DEFERRED")
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    product_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True, server_default=sa.text('gen_random_uuid()'))
    media_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="CASCADE"), nullable=False, index=True)
    variant_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True, index=True)
    is_primary: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"), index=True)
    
    product: Mapped["Product"] = relationship("Product", back_populates="media_associations")
    variant: Mapped["ProductVariant"] = relationship("ProductVariant", back_populates="media_associations")
    media: Mapped["Media"] = relationship("Media", back_populates="product_associations")
    
    def __repr__(self):
        return f"<ProductMedia(product_id={self.product_id}, media_id={self.media_id}, variant_id={self.variant_id}, is_primary={self.is_primary})>"