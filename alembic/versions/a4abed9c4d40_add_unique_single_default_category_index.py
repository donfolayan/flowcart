"""add unique single default category index

Revision ID: a4abed9c4d40
Revises: 4928ad6ec578
Create Date: 2025-11-05 16:09:56.351188

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql  # noqa: F401

revision: str = "a4abed9c4d40"
down_revision: Union[str, Sequence[str], None] = "4928ad6ec578"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        "uq_single_default_category",
        "categories",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default IS TRUE"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "uq_single_default_category",
        table_name="categories",
        postgresql_where=sa.text("is_default IS TRUE"),
    )
