from uuid import UUID
import sqlalchemy as sa
from sqlalchemy import event
from datetime import datetime
from typing import Optional
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.enums.promo_enum import PromoTypeEnum, promo_type

class PromoCode(Base):
    __tablename__ = "promo_codes"
    __table_args__ = (
        sa.CheckConstraint(
            "(promo_type = 'fixed_amount' AND value_cents IS NOT NULL AND percent_basis_points IS NULL) OR (promo_type = 'percentage' AND percent_basis_points IS NOT NULL AND value_cents IS NULL)",
            name="ck_promo_type_exclusive"
        ),
        sa.CheckConstraint("value_cents >= 0", name="ck_promocode_value_non_negative"),
        sa.CheckConstraint("percent_basis_points BETWEEN 1 AND 10000", name="ck_promocode_percent_basis_points_valid"),
        sa.CheckConstraint("max_discount_cents IS NULL OR max_discount_cents >= 0", name="ck_promocode_max_discount_non_negative"),
        sa.CheckConstraint("min_subtotal_cents IS NULL OR min_subtotal_cents >= 0", name="ck_promocode_min_subtotal_non_negative"),
        sa.CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="ck_promocode_usage_limit_positive"),
        sa.CheckConstraint("per_user_limit IS NULL OR per_user_limit > 0", name="ck_promocode_per_user_limit_positive"),
        sa.CheckConstraint("usage_count >= 0", name="ck_promocode_usage_count_non_negative"),
        sa.CheckConstraint("usage_limit IS NULL OR usage_count <= usage_limit", name="ck_promocode_usage_within_limit"),
        sa.CheckConstraint("starts_at IS NULL OR ends_at IS NULL OR starts_at < ends_at", name="ck_promocode_valid_timeframe"),
        sa.CheckConstraint("ends_at IS NULL OR ends_at > now()", name="ck_promocode_ends_at_future"),
    )
    
    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(sa.String(50), nullable=False, unique=True)
    promo_type: Mapped[PromoTypeEnum] = mapped_column(promo_type, nullable=False)
    
    value_cents: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    percent_basis_points: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    max_discount_cents: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    min_subtotal_cents: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    
    usage_limit: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    per_user_limit: Mapped[int] = mapped_column(sa.Integer, nullable=True)
    usage_count: Mapped[int] = mapped_column(sa.Integer, nullable=False, server_default=sa.text('0'))
    
    is_active: Mapped[bool] = mapped_column(sa.Boolean, nullable=False, server_default=sa.text('true'))
    
    starts_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    ends_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    
    applies_to_product_ids: Mapped[Optional[list[UUID]]] = mapped_column(sa.ARRAY(PGUUID(as_uuid=True)), nullable=True)
    applies_to_user_ids: Mapped[Optional[list[UUID]]] = mapped_column(sa.ARRAY(PGUUID(as_uuid=True)), nullable=True)
    
    extra_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True), nullable=True)
    
    
@event.listens_for(PromoCode, "before_insert")
def before_insert_promocode(mapper, connection, target: PromoCode) -> None:
    """Ensure that the promo code is stored in lowercase."""
    target.code = target.code.lower()

@event.listens_for(PromoCode, "before_update")
def before_update_promocode(mapper, connection, target: PromoCode) -> None:
    """Ensure that the promo code is stored in lowercase."""
    target.code = target.code.lower()