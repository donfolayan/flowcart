"""add session_id to order model

Revision ID: a0d0d8a9d1f3
Revises: 4fe2be15ffa3
Create Date: 2025-11-19 10:49:41.441160

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a0d0d8a9d1f3"
down_revision: Union[str, Sequence[str], None] = "4fe2be15ffa3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "orders", sa.Column("session_id", sa.String(length=128), nullable=True)
    )
    op.create_index(
        op.f("ix_orders_session_id"), "orders", ["session_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_orders_session_id"), table_name="orders")
    op.drop_column("orders", "session_id")
