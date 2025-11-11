"""create cart_items table

Revision ID: 8a4c7bc31c31
Revises: 68b6ee57c111
Create Date: 2025-11-10 23:47:55.248767

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "8a4c7bc31c31"
down_revision: Union[str, Sequence[str], None] = "68b6ee57c111"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "cart_items",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("cart_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("product_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("variant_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("product_name", sa.String(length=255), nullable=False),
        sa.Column("product_snapshot", sa.JSON(), nullable=False),
        sa.Column(
            "quantity", sa.Integer(), server_default=sa.text("1"), nullable=False
        ),
        sa.Column(
            "unit_price_currency",
            postgresql.ENUM(name="currency_enum", create_type=False),
            server_default=sa.text("'USD'::currency_enum"),
            nullable=False,
        ),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tax_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "line_total",
            sa.Numeric(precision=12, scale=2),
            sa.Computed(
                "((unit_price * quantity) - discount_amount + tax_amount)",
                persisted=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("quantity > 0", name="chk_cart_item_quantity_positive"),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "cart_id",
            "product_id",
            "variant_id",
            name="uq_cart_item_cart_product_variant",
        ),
    )
    op.create_index(
        op.f("ix_cart_items_cart_id"), "cart_items", ["cart_id"], unique=False
    )
    op.create_index(
        "ix_cart_items_cart_product",
        "cart_items",
        ["cart_id", "product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cart_items_created_at"), "cart_items", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_cart_items_product_id"), "cart_items", ["product_id"], unique=False
    )
    op.create_index(
        op.f("ix_cart_items_product_name"), "cart_items", ["product_name"], unique=False
    )
    op.create_index(
        op.f("ix_cart_items_updated_at"), "cart_items", ["updated_at"], unique=False
    )
    op.create_index(
        op.f("ix_cart_items_variant_id"), "cart_items", ["variant_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_cart_items_variant_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_updated_at"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_product_name"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_product_id"), table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_created_at"), table_name="cart_items")
    op.drop_index("ix_cart_items_cart_product", table_name="cart_items")
    op.drop_index(op.f("ix_cart_items_cart_id"), table_name="cart_items")
    op.drop_table("cart_items")
