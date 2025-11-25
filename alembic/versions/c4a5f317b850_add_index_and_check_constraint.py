"""add index and check constraint

Revision ID: c4a5f317b850
Revises: ddb21cf4186d
Create Date: 2025-11-24 21:46:17.199154

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a5f317b850"
down_revision: Union[str, Sequence[str], None] = "ddb21cf4186d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "ix_orders_idempotency_key_session_id",
        "orders",
        ["idempotency_key", "session_id"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_orders_idempotency_key_session_id",
        table_name="orders",
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
