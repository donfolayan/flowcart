"""Add indexes for performance to product table

Revision ID: b037eff9b756
Revises: 6a4c3ef43fe5
Create Date: 2025-11-05 22:48:36.263613

"""

from typing import Sequence, Union

from alembic import op


revision: str = "b037eff9b756"
down_revision: Union[str, Sequence[str], None] = "6a4c3ef43fe5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        op.f("ix_products_created_at"), "products", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_products_updated_at"), "products", ["updated_at"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_products_updated_at"), table_name="products")
    op.drop_index(op.f("ix_products_created_at"), table_name="products")
