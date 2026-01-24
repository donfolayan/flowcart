"""add verification fields to user model

Revision ID: 6354285357f5
Revises: 4bd7acce752a
Create Date: 2026-01-24 22:15:29.385047

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '6354285357f5'
down_revision: Union[str, Sequence[str], None] = '4bd7acce752a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('users', sa.Column('verification_token', sa.String(length=255), nullable=True))
    op.add_column('users', sa.Column('verification_token_expiry', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'verification_token_expiry')
    op.drop_column('users', 'verification_token')