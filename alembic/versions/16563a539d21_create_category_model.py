"""create category model

Revision ID: 16563a539d21
Revises: a631483fe943
Create Date: 2025-10-20 02:07:44.507722

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "16563a539d21"
down_revision: Union[str, Sequence[str], None] = "a631483fe943"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "categories",
        sa.Column(
            "id",
            postgresql.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column(
            "is_default", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("category_image_id", postgresql.UUID(), nullable=True),
        sa.ForeignKeyConstraint(
            ["category_image_id"], ["media.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_categories_category_image_id"),
        "categories",
        ["category_image_id"],
        unique=False,
    )
    op.create_index(op.f("ix_categories_name"), "categories", ["name"], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_categories_name"), table_name="categories")
    op.drop_index(op.f("ix_categories_category_image_id"), table_name="categories")
    op.drop_table("categories")
