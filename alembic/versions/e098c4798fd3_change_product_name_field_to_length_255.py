"""change product name field to length 255

Revision ID: e098c4798fd3
Revises: 1627785bd9e1
Create Date: 2025-11-08 17:09:33.697249

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e098c4798fd3"
down_revision: Union[str, Sequence[str], None] = "1627785bd9e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        "products",
        "name",
        existing_type=sa.VARCHAR(length=100),
        type_=sa.String(length=255),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        "products",
        "name",
        existing_type=sa.String(length=255),
        type_=sa.VARCHAR(length=100),
        existing_nullable=False,
    )
