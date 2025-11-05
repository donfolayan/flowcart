import sqlalchemy as sa
from uuid import UUID
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import event, select, update

from app.db.base import Base

if TYPE_CHECKING:
    from .product import Product
    from .media import Media


class Category(Base):
    __tablename__ = "categories"
    __table_args__ = (sa.Index("uq_single_default_category", "is_default", unique=True, postgresql_where=sa.text("is_default IS TRUE")),)

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    name: Mapped[str] = mapped_column(sa.String(100), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(sa.String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(sa.Boolean, server_default=sa.text("false"), nullable=False)
    category_image_id: Mapped[UUID | None] = mapped_column(PGUUID(as_uuid=True), sa.ForeignKey("media.id", ondelete="SET NULL"), nullable=True, index=True)
    
    products: Mapped[List["Product"]] = relationship("Product", back_populates="category")
    category_image: Mapped[Optional["Media"]] = relationship("Media", lazy="joined", foreign_keys=[category_image_id], back_populates="categories", passive_deletes=True)


    @classmethod
    def get_default(cls, connection):
        result = connection.execute(select(cls).where(cls.is_default.is_(True))).scalar_one_or_none()
        
        if not result:
            raise ValueError("No default category set.")        
        return result

    def __repr__(self):
        return f"<Category(name={self.name})>"
    
@event.listens_for(Category, "before_insert")
def ensure_single_default_category(mapper, connection, target):
    if target.is_default:
        connection.execute(
            update(sa.table("categories"))
            .where(sa.column("is_default").is_(sa.true()))
            .values(is_default=False)
        )

@event.listens_for(Category, "before_delete")
def reassign_products_to_default(mapper, connection, target):
    default_category_id: UUID = connection.scalar(select(Category.id).where(Category.is_default.is_(True), Category.id != target.id))

    if not default_category_id:
        raise ValueError("Cannot delete the default category or no default category set.")
    if target.is_default:
        raise ValueError("Cannot delete the default category.")

    connection.execute(
        update(sa.table("products"))
        .where(sa.column("category_id") == target.id)
        .values(category_id=default_category_id))