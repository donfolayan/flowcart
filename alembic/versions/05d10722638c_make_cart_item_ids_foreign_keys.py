"""make cart item ids foreign keys

Revision ID: 05d10722638c
Revises: a0d0d8a9d1f3
Create Date: 2025-11-19 11:18:45.833277

"""

from typing import Sequence, Union

from alembic import op


revision: str = "05d10722638c"
down_revision: Union[str, Sequence[str], None] = "a0d0d8a9d1f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_foreign_key(
        "fk_cart_items_product_id",
        "cart_items",
        "products",
        ["product_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_cart_items_variant_id",
        "cart_items",
        "product_variants",
        ["variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("fk_cart_items_variant_id", "cart_items", type_="foreignkey")
    op.drop_constraint("fk_cart_items_product_id", "cart_items", type_="foreignkey")
