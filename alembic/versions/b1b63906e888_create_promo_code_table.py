"""create promo code table

Revision ID: b1b63906e888
Revises: c4a5f317b850
Create Date: 2025-11-25 17:28:46.690605

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "b1b63906e888"
down_revision: Union[str, Sequence[str], None] = "c4a5f317b850"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    promo_type_enum = postgresql.ENUM(
        "percentage",
        "fixed_amount",
        "free_shipping",
        name="promo_type_enum",
    )
    promo_type_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "promo_codes",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column(
            "promo_type",
            postgresql.ENUM(name="promo_type_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("value_cents", sa.Integer(), nullable=True),
        sa.Column("percent_basis_points", sa.Integer(), nullable=True),
        sa.Column("max_discount_cents", sa.Integer(), nullable=True),
        sa.Column("min_subtotal_cents", sa.Integer(), nullable=True),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("per_user_limit", sa.Integer(), nullable=True),
        sa.Column(
            "usage_count", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column(
            "starts_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("ends_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("applies_to_product_ids", sa.ARRAY(sa.UUID()), nullable=True),
        sa.Column("applies_to_user_ids", sa.ARRAY(sa.UUID()), nullable=True),
        sa.Column("extra_data", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
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
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "(promo_type = 'fixed_amount' AND value_cents IS NOT NULL AND percent_basis_points IS NULL) OR (promo_type = 'percentage' AND percent_basis_points IS NOT NULL AND value_cents IS NULL)",
            name="ck_promo_type_exclusive",
        ),
        sa.CheckConstraint(
            "ends_at IS NULL OR ends_at > now()", name="ck_promocode_ends_at_future"
        ),
        sa.CheckConstraint(
            "max_discount_cents IS NULL OR max_discount_cents >= 0",
            name="ck_promocode_max_discount_non_negative",
        ),
        sa.CheckConstraint(
            "min_subtotal_cents IS NULL OR min_subtotal_cents >= 0",
            name="ck_promocode_min_subtotal_non_negative",
        ),
        sa.CheckConstraint(
            "per_user_limit IS NULL OR per_user_limit > 0",
            name="ck_promocode_per_user_limit_positive",
        ),
        sa.CheckConstraint(
            "percent_basis_points BETWEEN 1 AND 10000",
            name="ck_promocode_percent_basis_points_valid",
        ),
        sa.CheckConstraint(
            "starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at",
            name="ck_promocode_valid_timeframe",
        ),
        sa.CheckConstraint(
            "usage_count >= 0", name="ck_promocode_usage_count_non_negative"
        ),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_count <= usage_limit",
            name="ck_promocode_usage_within_limit",
        ),
        sa.CheckConstraint(
            "usage_limit IS NULL OR usage_limit > 0",
            name="ck_promocode_usage_limit_positive",
        ),
        sa.CheckConstraint("value_cents >= 0", name="ck_promocode_value_non_negative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("promo_codes")
    promo_type_enum = postgresql.ENUM(
        "percentage",
        "fixed_amount",
        "free_shipping",
        name="promo_type_enum",
    )
    promo_type_enum.drop(op.get_bind(), checkfirst=True)
