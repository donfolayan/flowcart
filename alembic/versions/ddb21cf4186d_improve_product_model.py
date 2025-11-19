"""improve product model

Revision ID: ddb21cf4186d
Revises: 05d10722638c
Create Date: 2025-11-19 11:34:15.347572

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "ddb21cf4186d"
down_revision: Union[str, Sequence[str], None] = "05d10722638c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "products",
        "attributes",
        existing_type=postgresql.JSON(astext_type=sa.Text()),
        type_=postgresql.JSONB(astext_type=sa.Text()),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "products",
        "attributes",
        existing_type=postgresql.JSONB(astext_type=sa.Text()),
        type_=postgresql.JSON(astext_type=sa.Text()),
        existing_nullable=True,
    )
