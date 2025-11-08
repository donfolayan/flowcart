"""create cart table

Revision ID: 68b6ee57c111
Revises: e098c4798fd3
Create Date: 2025-11-09 00:42:29.830596

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "68b6ee57c111"
down_revision: Union[str, Sequence[str], None] = "e098c4798fd3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "carts",
        sa.Column(
            "id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False
        ),
        sa.Column("user_id", sa.UUID(), nullable=True),
        sa.Column("session_id", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "active",
                "completed",
                "abandoned",
                "cancelled",
                "expired",
                "archived",
                name="cart_status",
            ),
            server_default=sa.text("'active'::cart_status"),
            nullable=False,
        ),
        sa.Column(
            "currency",
            postgresql.ENUM(
                "USD",
                "NGN",
                "EUR",
                "GBP",
                "JPY",
                "AUD",
                "CAD",
                "CHF",
                "CNY",
                "SEK",
                "NZD",
                name="currency_enum",
            ),
            server_default=sa.text("'USD'::currency_enum"),
            nullable=False,
        ),
        sa.Column(
            "subtotal",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "tax_total",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "discount_total",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "shipping_total",
            sa.Numeric(precision=10, scale=2),
            server_default=sa.text("0.00"),
            nullable=False,
        ),
        sa.Column(
            "total",
            sa.Numeric(precision=10, scale=2),
            sa.Computed(
                "((subtotal + shipping_total) - discount_total + tax_total)",
                persisted=True,
            ),
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
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("extra_data", sa.JSON(), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "user_id IS NOT NULL OR session_id IS NOT NULL",
            name="chk_carts_user_or_session",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_carts_created_at"), "carts", ["created_at"], unique=False)
    op.create_index(op.f("ix_carts_expires_at"), "carts", ["expires_at"], unique=False)
    op.create_index(op.f("ix_carts_session_id"), "carts", ["session_id"], unique=False)
    op.create_index(op.f("ix_carts_status"), "carts", ["status"], unique=False)
    op.create_index(op.f("ix_carts_updated_at"), "carts", ["updated_at"], unique=False)
    op.create_index(op.f("ix_carts_user_id"), "carts", ["user_id"], unique=False)
    op.create_index(
        "ix_carts_user_status", "carts", ["user_id", "status"], unique=False
    )
    op.create_index(
        "ux_carts_active_per_session_guest",
        "carts",
        ["session_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND user_id IS NULL"),
    )
    op.create_index(
        "ux_carts_active_per_user",
        "carts",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND user_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ux_carts_active_per_user",
        table_name="carts",
        postgresql_where=sa.text("status = 'active' AND user_id IS NOT NULL"),
    )
    op.drop_index(
        "ux_carts_active_per_session_guest",
        table_name="carts",
        postgresql_where=sa.text("status = 'active' AND user_id IS NULL"),
    )
    op.drop_index("ix_carts_user_status", table_name="carts")
    op.drop_index(op.f("ix_carts_user_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_updated_at"), table_name="carts")
    op.drop_index(op.f("ix_carts_status"), table_name="carts")
    op.drop_index(op.f("ix_carts_session_id"), table_name="carts")
    op.drop_index(op.f("ix_carts_expires_at"), table_name="carts")
    op.drop_index(op.f("ix_carts_created_at"), table_name="carts")
    op.drop_table("carts")
