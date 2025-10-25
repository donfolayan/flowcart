"""add is_admin field to user class

Revision ID: 29099fa06656
Revises: 10a5f3d5a635
Create Date: 2025-10-25 12:01:37.366047

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "29099fa06656"
down_revision: Union[str, Sequence[str], None] = "10a5f3d5a635"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "users",
        sa.Column(
            "is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("users", "is_admin")
