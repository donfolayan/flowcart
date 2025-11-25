"""add order promo fields and promo code indexes

Revision ID: d8b9f3a2c1a
Revises: b1b63906e888
Create Date: 2025-11-25 18:05:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d8b9f3a2c1a"
down_revision = "b1b63906e888"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add promo fields to orders
    op.add_column(
        "orders", sa.Column("promo_code", sa.String(length=50), nullable=True)
    )
    op.add_column(
        "orders",
        sa.Column(
            "applied_discounts_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
    )
    op.create_index("ix_orders_promo_code", "orders", ["promo_code"])

    # Add functional unique index on lower(code)
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_promocode_code_ci ON promo_codes (lower(code));"
    )

    # GIN indexes for array containment
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_promocode_product_ids_gin ON promo_codes USING gin (applies_to_product_ids);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_promocode_user_ids_gin ON promo_codes USING gin (applies_to_user_ids);"
    )

    # Composite index for active/time filtering
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_promocode_active_time ON promo_codes (is_active, starts_at, ends_at);"
    )


def downgrade() -> None:
    op.drop_index("ix_orders_promo_code", table_name="orders")
    op.drop_column("orders", "applied_discounts_snapshot")
    op.drop_column("orders", "promo_code")

    op.execute("DROP INDEX IF EXISTS ix_promocode_code_ci;")
    op.execute("DROP INDEX IF EXISTS ix_promocode_product_ids_gin;")
    op.execute("DROP INDEX IF EXISTS ix_promocode_user_ids_gin;")
    op.execute("DROP INDEX IF EXISTS ix_promocode_active_time;")
