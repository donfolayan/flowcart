"""create shippings table

Revision ID: 4fe2be15ffa3
Revises: 48492961468a
Create Date: 2025-11-19 10:43:03.033174

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "4fe2be15ffa3"
down_revision: Union[str, Sequence[str], None] = "48492961468a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    shipping_status_enum = postgresql.ENUM(
        "pending",
        "in_transit",
        "delivered",
        "delayed",
        "cancelled",
        name="shipping_status_enum",
    )
    shipping_status_enum.create(op.get_bind(), checkfirst=True)

    shipping_carrier_enum = postgresql.ENUM(
        "Gig Logistics", name="shipping_carrier_enum"
    )
    shipping_carrier_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "shippings",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("address_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "shipping_cents", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "shipping_tax_cents",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "carrier",
            postgresql.ENUM(name="shipping_carrier_enum", create_type=False),
            nullable=False,
        ),
        sa.Column("tracking_number", sa.String(length=100), nullable=True),
        sa.Column("tracking_url", sa.String(length=255), nullable=True),
        sa.Column("label_url", sa.String(length=255), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(name="shipping_status_enum", create_type=False),
            server_default=sa.text("'pending'::shipping_status_enum"),
            nullable=False,
        ),
        sa.Column("shipped_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
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
        sa.ForeignKeyConstraint(["address_id"], ["addresses.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", name="uq_shippings_order_id"),
    )
    op.create_index(
        op.f("ix_shippings_address_id"), "shippings", ["address_id"], unique=False
    )
    op.create_index(
        op.f("ix_shippings_order_id"), "shippings", ["order_id"], unique=True
    )
    op.add_column(
        "order_items",
        sa.Column("product_image_url", sa.String(length=500), nullable=True),
    )
    op.create_index(
        "ix_orderitem_order_product_variant",
        "order_items",
        ["order_id", "product_id", "variant_id"],
        unique=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_orderitem_order_product_variant", table_name="order_items")
    op.drop_column("order_items", "product_image_url")
    op.drop_index(op.f("ix_shippings_order_id"), table_name="shippings")
    op.drop_index(op.f("ix_shippings_address_id"), table_name="shippings")
    op.drop_table("shippings")

    shipping_carrier_enum = postgresql.ENUM(
        "Gig Logistics", name="shipping_carrier_enum"
    )
    shipping_carrier_enum.drop(op.get_bind(), checkfirst=True)

    shipping_status_enum = postgresql.ENUM(
        "pending",
        "in_transit",
        "delivered",
        "delayed",
        "cancelled",
        name="shipping_status_enum",
    )
    shipping_status_enum.drop(op.get_bind(), checkfirst=True)
