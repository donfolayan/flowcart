"""add index constraints to product media

Revision ID: 1627785bd9e1
Revises: b037eff9b756
Create Date: 2025-11-06 07:44:16.240059

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1627785bd9e1"
down_revision: Union[str, Sequence[str], None] = "b037eff9b756"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_product_media_is_primary"), table_name="product_media")
    op.drop_constraint(
        op.f("uix_product_media_unique"), "product_media", type_="unique"
    )
    op.drop_constraint(
        op.f("uix_product_primary_image"), "product_media", type_="unique"
    )
    op.create_index(
        "uix_product_primary_image",
        "product_media",
        ["product_id"],
        unique=True,
        postgresql_where=sa.text("is_primary = true"),
    )
    op.create_index(
        "uix_product_media_product_media_variant_not_null",
        "product_media",
        ["product_id", "media_id", "variant_id"],
        unique=True,
        postgresql_where=sa.text("variant_id IS NOT NULL"),
    )
    op.create_index(
        "uix_product_media_product_media_variant_null",
        "product_media",
        ["product_id", "media_id"],
        unique=True,
        postgresql_where=sa.text("variant_id IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uix_product_media_product_media_variant_null",
        table_name="product_media",
        postgresql_where=sa.text("variant_id IS NULL"),
    )
    op.drop_index(
        "uix_product_media_product_media_variant_not_null",
        table_name="product_media",
        postgresql_where=sa.text("variant_id IS NOT NULL"),
    )
    op.drop_index(
        "uix_product_primary_image",
        table_name="product_media",
        postgresql_where=sa.text("is_primary = true"),
    )
    op.create_unique_constraint(
        op.f("uix_product_primary_image"),
        "product_media",
        ["product_id", "is_primary"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_unique_constraint(
        op.f("uix_product_media_unique"),
        "product_media",
        ["product_id", "media_id", "variant_id"],
        postgresql_nulls_not_distinct=False,
    )
    op.create_index(
        op.f("ix_product_media_is_primary"),
        "product_media",
        ["is_primary"],
        unique=False,
    )
