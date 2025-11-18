"""create payment table

Revision ID: 48492961468a
Revises: 2d49559c3a11
Create Date: 2025-11-18 16:23:46.394119

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "48492961468a"
down_revision: Union[str, Sequence[str], None] = "2d49559c3a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    payment_status_enum = postgresql.ENUM(
        "pending",
        "processing",
        "authorized",
        "completed",
        "cancelled",
        "failed",
        "refunded",
        "partially_refunded",
        name="payment_status_enum",
    )
    payment_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "payments",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("provider_id", sa.String(length=255), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(name="payment_status_enum", create_type=False),
            server_default=sa.text("'pending'::payment_status_enum"),
            nullable=False,
        ),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column(
            "currency",
            postgresql.ENUM(name="currency_enum", create_type=False),
            server_default=sa.text("'USD'::currency_enum"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_payments_order_id"),
    )
    op.create_index(op.f("ix_payments_order_id"), "payments", ["order_id"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_payments_order_id"), table_name="payments")
    op.drop_table("payments")
    payment_status_enum = postgresql.ENUM(
        "pending", "completed", "failed", "refunded", name="payment_status_enum"
    )
    payment_status_enum.drop(op.get_bind(), checkfirst=True)
