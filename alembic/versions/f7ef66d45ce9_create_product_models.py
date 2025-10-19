"""create product models

Revision ID: f7ef66d45ce9
Revises: 2f2969c37d53
Create Date: 2025-10-19 11:38:01.015453

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "f7ef66d45ce9"
down_revision: Union[str, Sequence[str], None] = "2f2969c37d53"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "products",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column(
            "is_variable", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("stock", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            onupdate=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "is_deleted", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
        sa.UniqueConstraint("slug"),
        sa.CheckConstraint("stock >= 0", name="chk_products_stock_nonnegative"),
        sa.CheckConstraint(
            "base_price >= 0", name="chk_products_base_price_nonnegative"
        ),
    )

    op.create_index(op.f("ix_products_name"), "products", ["name"], unique=False)
    op.create_table(
        "product_variants",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
        sa.CheckConstraint("stock >= 0", name="chk_product_variants_stock_nonnegative"),
        sa.CheckConstraint("price >= 0", name="chk_product_variants_price_nonnegative"),
    )

    op.create_table(
        "product_images",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("image_url", sa.String(length=255), nullable=True),
        sa.Column("alt_text", sa.String(length=150), nullable=True),
        sa.Column(
            "is_variant_image",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("product_images")
    op.drop_table("product_variants")
    op.drop_index(op.f("ix_products_name"), table_name="products")
    op.drop_table("products")
