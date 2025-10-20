"""create product_media table

Revision ID: a631483fe943
Revises: 7307cb37b81c
Create Date: 2025-10-20 01:54:18.713349

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "a631483fe943"
down_revision: Union[str, Sequence[str], None] = "7307cb37b81c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "product_media",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("product_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("media_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "is_primary", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.ForeignKeyConstraint(["media_id"], ["media.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["variant_id"], ["product_variants.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "is_primary",
            deferrable=True,
            initially="DEFERRED",
            name="uix_product_primary_image",
        ),
        sa.UniqueConstraint(
            "product_id", "media_id", "variant_id", name="uix_product_media_unique"
        ),
    )
    op.create_index(
        op.f("ix_product_media_media_id"), "product_media", ["media_id"], unique=False
    )
    op.create_index(
        op.f("ix_product_media_product_id"),
        "product_media",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_media_variant_id"),
        "product_media",
        ["variant_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_media_is_primary"),
        "product_media",
        ["is_primary"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_product_media_variant_id"), table_name="product_media")
    op.drop_index(op.f("ix_product_media_product_id"), table_name="product_media")
    op.drop_index(op.f("ix_product_media_media_id"), table_name="product_media")
    op.drop_table("product_media")
