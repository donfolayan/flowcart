"""modify Product models

Revision ID: 10a5f3d5a635
Revises: 16563a539d21
Create Date: 2025-10-25 11:22:56.524286

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "10a5f3d5a635"
down_revision: Union[str, Sequence[str], None] = "16563a539d21"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    postgresql.ENUM("draft", "active", "archived", name="variant_status").create(
        bind, checkfirst=True
    )
    postgresql.ENUM("draft", "active", "archived", name="product_status").create(
        bind, checkfirst=True
    )

    op.add_column("product_variants", sa.Column("product_id", sa.UUID(), nullable=True))
    op.add_column(
        "product_variants",
        sa.Column(
            "status",
            postgresql.ENUM("draft", "active", "archived", name="variant_status"),
            server_default=sa.text("'draft'::variant_status"),
            nullable=False,
        ),
    )
    op.alter_column(
        "product_variants",
        "price",
        existing_type=sa.NUMERIC(precision=10, scale=2),
        nullable=True,
    )
    op.drop_index(
        op.f("ix_product_variants_base_product_id"), table_name="product_variants"
    )
    op.create_index(
        op.f("ix_product_variants_product_id"),
        "product_variants",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_variants_status"), "product_variants", ["status"], unique=False
    )
    op.execute(
        "UPDATE product_variants SET product_id = base_product_id WHERE product_id IS NULL and base_product_id IS NOT NULL"
    )
    op.drop_constraint(
        op.f("product_variants_base_product_id_fkey"),
        "product_variants",
        type_="foreignkey",
    )
    op.create_foreign_key(
        None,
        "product_variants",
        "products",
        ["product_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_column("product_variants", "base_product_id")
    op.add_column(
        "products",
        sa.Column(
            "status",
            postgresql.ENUM("draft", "active", "archived", name="product_status"),
            server_default=sa.text("'draft'::product_status"),
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE products SET status = CASE WHEN is_active = true THEN 'active'::product_status ELSE 'draft'::product_status END WHERE status IS NULL"
    )
    op.create_index(op.f("ix_products_status"), "products", ["status"], unique=False)
    op.drop_column("products", "is_active")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.add_column(
        "products",
        sa.Column(
            "is_active",
            sa.BOOLEAN(),
            server_default=sa.text("true"),
            autoincrement=False,
            nullable=False,
        ),
    )
    op.execute(
        "UPDATE products SET is_active = CASE WHEN status = 'active' THEN true ELSE false END WHERE is_active IS NULL"
    )
    op.drop_index(op.f("ix_products_status"), table_name="products")
    op.drop_column("products", "status")
    op.add_column(
        "product_variants", sa.Column("base_product_id", sa.UUID(), nullable=True)
    )
    op.execute(
        "UPDATE product_variants SET base_product_id = product_id WHERE base_product_id IS NULL AND product_id IS NOT NULL"
    )
    op.create_foreign_key(
        op.f("product_variants_base_product_id_fkey"),
        "product_variants",
        "products",
        ["base_product_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        op.f("fk_product_variants_product_id_products"),
        "product_variants",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_product_variants_status"), table_name="product_variants")
    op.drop_index(op.f("ix_product_variants_product_id"), table_name="product_variants")
    op.execute("UPDATE product_variants SET price = 0 WHERE price IS NULL")
    op.alter_column(
        "product_variants",
        "price",
        existing_type=sa.NUMERIC(precision=10, scale=2),
        nullable=False,
    )
    op.drop_column("product_variants", "status")
    op.drop_column("product_variants", "product_id")
    op.create_index(
        op.f("ix_product_variants_base_product_id"),
        "product_variants",
        ["base_product_id"],
        unique=False,
    )
    postgresql.ENUM("draft", "active", "archived", name="variant_status").drop(
        bind, checkfirst=True
    )
    postgresql.ENUM("draft", "active", "archived", name="product_status").drop(
        bind, checkfirst=True
    )
