"""add uploaded_at field to ProductMedia class

Revision ID: 7211f474ca02
Revises: 29099fa06656
Create Date: 2025-10-25 21:54:04.359657

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7211f474ca02"
down_revision: Union[str, Sequence[str], None] = "29099fa06656"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "product_media",
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("product_media", "uploaded_at")
