"""make variants delete on prroduct delete

Revision ID: 1487a7e655f4
Revises: 7211f474ca02
Create Date: 2025-10-26 14:15:50.980434

"""

from typing import Sequence, Union

from alembic import op

revision: str = "1487a7e655f4"
down_revision: Union[str, Sequence[str], None] = "7211f474ca02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        op.f("product_variants_product_id_fkey"), "product_variants", type_="foreignkey"
    )
    op.create_foreign_key(
        "fk_product_variants_product_id",
        "product_variants",
        "products",
        ["product_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_product_variants_product_id", "product_variants", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("product_variants_product_id_fkey"),
        "product_variants",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
