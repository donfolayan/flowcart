"""add charge_id and refund_id to payment table

Revision ID: ba6972dd8d0b
Revises: 3baf68fc4ddb
Create Date: 2026-01-23 18:02:45.972354

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ba6972dd8d0b"
down_revision: Union[str, Sequence[str], None] = "3baf68fc4ddb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "payments", sa.Column("charge_id", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "payments", sa.Column("refund_id", sa.String(length=255), nullable=True)
    )
    op.create_index(
        op.f("ix_payments_charge_id"), "payments", ["charge_id"], unique=False
    )
    op.create_index(
        op.f("ix_payments_refund_id"), "payments", ["refund_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_payments_refund_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_charge_id"), table_name="payments")
    op.drop_column("payments", "refund_id")
    op.drop_column("payments", "charge_id")
