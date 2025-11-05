"""add category fields to product table

Revision ID: 6a4c3ef43fe5
Revises: a4abed9c4d40
Create Date: 2025-11-05 17:59:03.553028

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "6a4c3ef43fe5"
down_revision: Union[str, Sequence[str], None] = "a4abed9c4d40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products", sa.Column("category_id", postgresql.UUID(), nullable=True)
    )
    op.create_index(
        op.f("ix_products_category_id"), "products", ["category_id"], unique=False
    )
    op.create_foreign_key(
        "fk_products_category_id_categories",
        "products",
        "categories",
        ["category_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "fk_products_category_id_categories", "products", type_="foreignkey"
    )
    op.drop_index(op.f("ix_products_category_id"), table_name="products")
    op.drop_column("products", "category_id")
