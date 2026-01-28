"""add password reset token and expiry

Revision ID: 1426ae9f1318
Revises: 6354285357f5
Create Date: 2026-01-28 17:25:33.223618

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1426ae9f1318'
down_revision: Union[str, Sequence[str], None] = '6354285357f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('password_reset_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('password_reset_token_expiry', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'password_reset_token_expiry')
    op.drop_column('users', 'password_reset_token')