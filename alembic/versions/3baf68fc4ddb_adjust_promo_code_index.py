"""Adjust promo code index

Revision ID: 3baf68fc4ddb
Revises: d8b9f3a2c1a
Create Date: 2025-11-29 16:12:32.183735

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "3baf68fc4ddb"
down_revision: Union[str, Sequence[str], None] = "d8b9f3a2c1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_index(op.f("ix_promocode_active_time"), table_name="promo_codes")
    op.create_index(
        "ix_promocode_active_time",
        "promo_codes",
        ["code", "is_active", "starts_at", "ends_at"],
        unique=False,
        postgresql_where=sa.text("is_active = true"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_promocode_active_time",
        table_name="promo_codes",
        postgresql_where=sa.text("is_active = true"),
    )
    op.create_index(
        op.f("ix_promocode_active_time"),
        "promo_codes",
        ["is_active", "starts_at", "ends_at"],
        unique=False,
    )
