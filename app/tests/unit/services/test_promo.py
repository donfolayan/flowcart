import asyncio
from types import SimpleNamespace
from datetime import datetime, timezone, timedelta
import pytest
from fastapi import HTTPException
from uuid import uuid4

from app.services.promo import PromoService
from app.enums.promo_enum import PromoTypeEnum
from typing import cast, Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.promo_code import PromoCode


class DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one(self):
        return self._value

    def scalar_one_or_none(self):
        return self._value


class DummyDB:
    def __init__(self, execute_result=None):
        self._execute_result = execute_result

    async def execute(self, stmt):
        # emulate SQLAlchemy result object
        await asyncio.sleep(0)
        return self._execute_result


@pytest.mark.parametrize(
    "basis_points, subtotal, expected", [(2500, 10000, 2500), (10000, 500, 500)]
)
def test_compute_percentage_discount(basis_points, subtotal, expected):
    svc = PromoService(db=cast(AsyncSession, None))
    promo = SimpleNamespace(
        promo_type=PromoTypeEnum.PERCENTAGE,
        percent_basis_points=basis_points,
        value_cents=None,
        max_discount_cents=None,
    )

    discount = svc._compute_discount(cast(PromoCode, promo), subtotal)
    assert discount == expected


def test_compute_fixed_discount_and_max():
    svc = PromoService(db=cast(AsyncSession, None))
    promo = SimpleNamespace(
        promo_type=PromoTypeEnum.FIXED_AMOUNT,
        percent_basis_points=None,
        value_cents=300,
        max_discount_cents=200,
    )

    discount = svc._compute_discount(cast(PromoCode, promo), subtotal_cents=1000)
    assert discount == 200


@pytest.mark.asyncio
async def test_validate_and_compute_success_and_snapshots(monkeypatch):
    now = datetime.now(timezone.utc)
    promo_obj = SimpleNamespace(
        id=1,
        code="WINTER",
        promo_type=PromoTypeEnum.FIXED_AMOUNT,
        value_cents=500,
        percent_basis_points=None,
        max_discount_cents=None,
        is_active=True,
        starts_at=now - timedelta(days=1),
        ends_at=now + timedelta(days=1),
        min_subtotal_cents=None,
        per_user_limit=None,
        usage_limit=None,
        usage_count=0,
        applies_to_user_ids=None,
    )

    svc = PromoService(db=cast(AsyncSession, DummyDB()))

    async def fake_get_by_code(code):
        assert code.lower() == "winter"
        return promo_obj

    monkeypatch.setattr(svc, "get_by_code", fake_get_by_code)

    res = await svc.validate_and_compute("winter", subtotal_cents=2000, user_id=None)
    assert res["discount_cents"] == 500
    assert res["promo"].code == "WINTER"
    assert "computed_discount_cents" in res["snapshot"]


@pytest.mark.asyncio
async def test_validate_and_compute_invalid_code(monkeypatch):
    svc = PromoService(db=cast(AsyncSession, DummyDB()))

    async def fake_get_by_code(code):
        return None

    monkeypatch.setattr(svc, "get_by_code", fake_get_by_code)

    with pytest.raises(HTTPException):
        await svc.validate_and_compute("nosuch", subtotal_cents=1000, user_id=None)


@pytest.mark.asyncio
async def test_increment_usage_atomic_success_and_failure(monkeypatch):
    # success: db.execute returns result with scalar_one_or_none -> new count
    db = DummyDB(execute_result=DummyResult(5))
    svc = PromoService(db=cast(AsyncSession, db))

    new_count = await svc.increment_usage_atomic(promo_id=1)
    assert isinstance(new_count, int)

    # failure: returns None -> should raise HTTPException
    db_fail = DummyDB(execute_result=DummyResult(None))
    svc_fail = PromoService(db=cast(AsyncSession, db_fail))

    with pytest.raises(HTTPException):
        await svc_fail.increment_usage_atomic(promo_id=1)


def test_compute_percentage_missing_basis_raises():
    svc = PromoService(db=cast(AsyncSession, None))
    promo = SimpleNamespace(
        promo_type=PromoTypeEnum.PERCENTAGE,
        percent_basis_points=None,
        value_cents=None,
        max_discount_cents=None,
    )

    with pytest.raises(HTTPException):
        svc._compute_discount(cast(PromoCode, promo), subtotal_cents=10000)


@pytest.mark.asyncio
async def test_validate_and_compute_various_failure_branches():
    now = datetime.now(timezone.utc)

    async def run_with(promo_obj, db_exec=None, user_id=None, subtotal=1000):
        svc = PromoService(db=cast(AsyncSession, db_exec or DummyDB()))

        async def fake_get(code):
            return promo_obj

        svc.get_by_code = fake_get
        with pytest.raises(HTTPException):
            await svc.validate_and_compute(
                code=promo_obj.code, subtotal_cents=subtotal, user_id=user_id
            )

    # not active
    promo_na = SimpleNamespace(
        id=1,
        code="NA",
        promo_type=PromoTypeEnum.FIXED_AMOUNT,
        value_cents=100,
        percent_basis_points=None,
        max_discount_cents=None,
        is_active=False,
        starts_at=None,
        ends_at=None,
        min_subtotal_cents=None,
        per_user_limit=None,
        usage_limit=None,
        usage_count=0,
        applies_to_user_ids=None,
    )
    await run_with(promo_na)

    # not started
    promo_ns = SimpleNamespace(
        **{**promo_na.__dict__, "is_active": True, "starts_at": now + timedelta(days=1)}
    )
    await run_with(promo_ns)

    # expired
    promo_ex = SimpleNamespace(
        **{
            **promo_na.__dict__,
            "is_active": True,
            "starts_at": now - timedelta(days=2),
            "ends_at": now - timedelta(days=1),
        }
    )
    await run_with(promo_ex)

    # min subtotal not met
    promo_min = SimpleNamespace(
        **{
            **promo_na.__dict__,
            "is_active": True,
            "starts_at": now - timedelta(days=1),
            "ends_at": now + timedelta(days=1),
            "min_subtotal_cents": 2000,
        }
    )
    await run_with(promo_min, subtotal=1000)

    # per-user limit requires auth
    promo_pul = SimpleNamespace(
        **{**promo_na.__dict__, "is_active": True, "per_user_limit": 1}
    )
    await run_with(promo_pul, user_id=None)

    # per-user limit reached (db returns count >= limit)
    db_count = DummyDB(execute_result=DummyResult(1))
    promo_pul2 = SimpleNamespace(
        **{**promo_na.__dict__, "is_active": True, "per_user_limit": 1}
    )
    svc = PromoService(db=cast(AsyncSession, db_count))

    async def fake_get2(code):
        return promo_pul2

    cast(Any, svc).get_by_code = fake_get2
    with pytest.raises(HTTPException):
        await svc.validate_and_compute(
            code=promo_pul2.code, subtotal_cents=1000, user_id=uuid4()
        )

    # usage limit reached
    promo_ul = SimpleNamespace(
        **{**promo_na.__dict__, "is_active": True, "usage_limit": 1, "usage_count": 1}
    )
    await run_with(promo_ul)

    # user targeting not eligible
    promo_ut = SimpleNamespace(
        **{
            **promo_na.__dict__,
            "is_active": True,
            "applies_to_user_ids": [str(uuid4())],
        }
    )
    await run_with(promo_ut, user_id=uuid4())
