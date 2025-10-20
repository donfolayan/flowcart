"""create Product variant table

Revision ID: 7307cb37b81c
Revises: 17b5af68c8d2
Create Date: 2025-10-20 01:49:25.919412

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "7307cb37b81c"
down_revision: Union[str, Sequence[str], None] = "17b5af68c8d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "product_variants",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("base_product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("sku", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("stock", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=True),
        sa.Column("primary_image_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.CheckConstraint("price >= 0", name="chk_product_variant_price_non_negative"),
        sa.CheckConstraint("stock >= 0", name="chk_product_variant_stock_non_negative"),
        sa.ForeignKeyConstraint(
            ["base_product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["primary_image_id"], ["media.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("sku"),
    )
    op.create_index(
        op.f("ix_product_variants_base_product_id"),
        "product_variants",
        ["base_product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_variants_primary_image_id"),
        "product_variants",
        ["primary_image_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        op.f("ix_product_variants_primary_image_id"), table_name="product_variants"
    )
    op.drop_index(
        op.f("ix_product_variants_base_product_id"), table_name="product_variants"
    )
    op.drop_table("product_variants")
