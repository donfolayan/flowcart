from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from fastapi import status
from app.core.errors import http_error

from app.models.promo_code import PromoCode
from app.models.order import Order
from app.enums.promo_enum import PromoTypeEnum


class PromoService:
    """Handles promo retrieval, validation, discount computation and usage updates."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_code(self, code: str) -> Optional[PromoCode]:
        """Return PromoCode by code (case-insensitive) or None."""
        normalized = code.strip().lower()
        stmt = select(PromoCode).where(func.lower(PromoCode.code) == normalized)
        res = await self.db.execute(stmt)
        return res.scalar_one_or_none()

    def _compute_discount(self, promo: PromoCode, subtotal_cents: int) -> int:
        if promo.promo_type == PromoTypeEnum.PERCENTAGE:
            if not promo.percent_basis_points:
                http_error(
                    "INVALID_PROMO_CONFIGURATION",
                    "Promo is misconfigured (missing basis points)",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            discount = (subtotal_cents * promo.percent_basis_points) // 10000
        else:
            discount = promo.value_cents or 0

        if promo.max_discount_cents is not None:
            discount = min(discount, promo.max_discount_cents)

        discount = max(0, min(discount, subtotal_cents))
        return int(discount)

    async def validate_and_compute(
        self, code: str, subtotal_cents: int, user_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """Validate promo and compute discount. Returns dict with keys: promo, discount_cents, snapshot.

        Raises HTTPException on invalid promo conditions.
        """
        promo = await self.get_by_code(code)
        if not promo:
            http_error(
                "INVALID_PROMO_CODE",
                "Promo code not found",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        assert promo is not None

        now = datetime.now(timezone.utc)
        if not promo.is_active:
            http_error(
                "PROMO_NOT_ACTIVE",
                "Promo is not active",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if promo.starts_at and promo.starts_at > now:
            http_error(
                "PROMO_NOT_STARTED",
                "Promo not yet active",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if promo.ends_at and promo.ends_at <= now:
            http_error(
                "PROMO_EXPIRED",
                "Promo has expired",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if promo.min_subtotal_cents and subtotal_cents < promo.min_subtotal_cents:
            http_error(
                "PROMO_MIN_SUBTOTAL_NOT_MET",
                "Minimum subtotal not met for promo",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # per-user limit
        if promo.per_user_limit is not None:
            if not user_id:
                http_error(
                    "PROMO_PER_USER_LIMIT_REQUIRES_AUTH",
                    "Promo requires authenticated user for per-user limit",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )
            count_stmt = (
                select(func.count())
                .select_from(Order)
                .where(
                    Order.user_id == user_id,
                    func.lower(Order.promo_code) == promo.code.lower(),
                )
            )
            cnt = (await self.db.execute(count_stmt)).scalar_one()
            if cnt >= promo.per_user_limit:
                http_error(
                    "PROMO_PER_USER_LIMIT_REACHED",
                    "Per-user promo usage limit reached",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        # global usage limit (soft check — final enforcement done during increment)
        if promo.usage_limit is not None and promo.usage_count >= promo.usage_limit:
            http_error(
                "PROMO_USAGE_LIMIT_REACHED",
                "Promo global usage limit reached",
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        # user-targeting list
        if promo.applies_to_user_ids:
            if not user_id or str(user_id) not in [
                str(u) for u in promo.applies_to_user_ids
            ]:
                http_error(
                    "PROMO_NOT_ELIGIBLE",
                    "User not eligible for this promo",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

        discount = self._compute_discount(promo, subtotal_cents)

        snapshot = {
            "promo_code": promo.code,
            "type": promo.promo_type.value
            if hasattr(promo.promo_type, "value")
            else str(promo.promo_type),
            "raw_value_cents": promo.value_cents,
            "percent_basis_points": promo.percent_basis_points,
            "max_discount_cents": promo.max_discount_cents,
            "computed_discount_cents": discount,
        }

        return {"promo": promo, "discount_cents": discount, "snapshot": snapshot}

    async def increment_usage_atomic(self, promo_id) -> int:
        """Atomically increment usage_count and update last_used_at. Returns new usage_count.

        Raises HTTPException if usage limit has been reached.
        """
        stmt = (
            PromoCode.__table__.update()
            .where(
                PromoCode.id == promo_id,
                (PromoCode.usage_limit.is_(None))
                | (PromoCode.usage_count < PromoCode.usage_limit),
            )
            .values(usage_count=PromoCode.usage_count + 1, last_used_at=func.now())
            .returning(PromoCode.usage_count)
        )
        result = await self.db.execute(stmt)
        new_count = result.scalar_one_or_none()
        if new_count is None:
            http_error(
                "PROMO_USAGE_LIMIT_REACHED",
                "Promo usage limit reached",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        assert new_count is not None
        return int(new_count)
