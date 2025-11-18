"""create order table

Revision ID: 039107460e92
Revises: b08e8ba077c0
Create Date: 2025-11-17 10:45:37.860700

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "039107460e92"
down_revision: Union[str, Sequence[str], None] = "b08e8ba077c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    order_status_enum = postgresql.ENUM(
        "pending",
        "awaiting_payment",
        "authorized",
        "paid",
        "fulfilled",
        "cancelled",
        "refunded",
        name="order_status_enum",
    )
    order_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "orders",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column("cart_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "currency",
            postgresql.ENUM(name="currency_enum", create_type=False),
            server_default=sa.text("'USD'::currency_enum"),
            nullable=False,
        ),
        sa.Column(
            "subtotal_cents", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "tax_cents", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "discount_cents", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column(
            "total_cents", sa.Integer(), server_default=sa.text("0"), nullable=False
        ),
        sa.Column("shipping_address_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "billing_address_same_as_shipping",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
        ),
        sa.Column("billing_address_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "shipping_address_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "billing_address_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "status",
            postgresql.ENUM(name="order_status_enum", create_type=False),
            server_default=sa.text("'pending'::order_status_enum"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("placed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fulfilled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("idempotency_key", sa.String(length=128), nullable=True),
        sa.Column("external_reference", sa.String(length=255), nullable=True),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.CheckConstraint(
            "discount_cents >= 0", name="ck_order_discount_non_negative"
        ),
        sa.CheckConstraint(
            "subtotal_cents >= 0", name="ck_order_subtotal_non_negative"
        ),
        sa.CheckConstraint("tax_cents >= 0", name="ck_order_tax_non_negative"),
        sa.CheckConstraint("total_cents >= 0", name="ck_order_total_non_negative"),
        sa.CheckConstraint("version >= 1", name="ck_order_version_positive"),
        sa.ForeignKeyConstraint(
            ["billing_address_id"], ["addresses.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["cart_id"], ["carts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["shipping_address_id"], ["addresses.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_orders_billing_address_id"),
        "orders",
        ["billing_address_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_canceled_at"), "orders", ["canceled_at"], unique=False
    )
    op.create_index(op.f("ix_orders_cart_id"), "orders", ["cart_id"], unique=False)
    op.create_index(
        op.f("ix_orders_created_at"), "orders", ["created_at"], unique=False
    )
    op.create_index(
        op.f("ix_orders_external_reference"),
        "orders",
        ["external_reference"],
        unique=False,
    )
    op.create_index(
        op.f("ix_orders_fulfilled_at"), "orders", ["fulfilled_at"], unique=False
    )
    op.create_index(
        "ix_orders_idempotency_key_user_id",
        "orders",
        ["idempotency_key", "user_id"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.create_index(op.f("ix_orders_paid_at"), "orders", ["paid_at"], unique=False)
    op.create_index(op.f("ix_orders_placed_at"), "orders", ["placed_at"], unique=False)
    op.create_index(
        op.f("ix_orders_shipping_address_id"),
        "orders",
        ["shipping_address_id"],
        unique=False,
    )
    op.create_index(op.f("ix_orders_status"), "orders", ["status"], unique=False)
    op.create_index(
        op.f("ix_orders_updated_at"), "orders", ["updated_at"], unique=False
    )
    op.create_index(op.f("ix_orders_user_id"), "orders", ["user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_orders_user_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_updated_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_status"), table_name="orders")
    op.drop_index(op.f("ix_orders_shipping_address_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_placed_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_paid_at"), table_name="orders")
    op.drop_index(
        "ix_orders_idempotency_key_user_id",
        table_name="orders",
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
    )
    op.drop_index(op.f("ix_orders_fulfilled_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_external_reference"), table_name="orders")
    op.drop_index(op.f("ix_orders_created_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_cart_id"), table_name="orders")
    op.drop_index(op.f("ix_orders_canceled_at"), table_name="orders")
    op.drop_index(op.f("ix_orders_billing_address_id"), table_name="orders")
    op.drop_table("orders")

    order_status_enum = postgresql.ENUM(
        "pending",
        "awaiting_payment",
        "authorized",
        "paid",
        "fulfilled",
        "cancelled",
        "refunded",
        name="order_status_enum",
    )
    order_status_enum.drop(op.get_bind(), checkfirst=True)
