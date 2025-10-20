"""create Media table

Revision ID: 8a5d7e4db0b4
Revises: ac0fd680ddbb
Create Date: 2025-10-20 01:39:40.742327

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "8a5d7e4db0b4"
down_revision: Union[str, Sequence[str], None] = "ac0fd680ddbb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "media",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("file_url", sa.String(length=255), nullable=False),
        sa.Column("alt_text", sa.String(length=150), nullable=True),
        sa.Column("mime_type", sa.String(length=50), nullable=False),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("uploaded_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_media_uploaded_at"), "media", ["uploaded_at"], unique=False
    )
    op.create_index(
        op.f("ix_media_uploaded_by"), "media", ["uploaded_by"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_media_uploaded_by"), table_name="media")
    op.drop_index(op.f("ix_media_uploaded_at"), table_name="media")
    op.drop_table("media")
