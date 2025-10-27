"""add provider info to media model

Revision ID: 4928ad6ec578
Revises: 1487a7e655f4
Create Date: 2025-10-27 18:25:02.636227

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4928ad6ec578"
down_revision: Union[str, Sequence[str], None] = "1487a7e655f4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("media", sa.Column("provider", sa.String(length=100), nullable=True))
    op.add_column(
        "media", sa.Column("provider_public_id", sa.String(length=200), nullable=True)
    )
    op.add_column(
        "media",
        sa.Column(
            "provider_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True
        ),
    )
    op.add_column(
        "media",
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
    )
    op.create_index(op.f("ix_media_is_active"), "media", ["is_active"], unique=False)
    op.create_index(op.f("ix_media_provider"), "media", ["provider"], unique=False)
    op.create_index(
        op.f("ix_media_provider_public_id"),
        "media",
        ["provider_public_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_media_provider_public_id"), table_name="media")
    op.drop_index(op.f("ix_media_provider"), table_name="media")
    op.drop_index(op.f("ix_media_is_active"), table_name="media")
    op.drop_column("media", "is_active")
    op.drop_column("media", "provider_metadata")
    op.drop_column("media", "provider_public_id")
    op.drop_column("media", "provider")
