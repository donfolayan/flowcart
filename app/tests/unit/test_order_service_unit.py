import asyncio
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order import OrderService
from app.services.promo import PromoService
from app.core.config import config


class _NoOpLoad:
    def selectinload(self, *a, **k):
        return self


@pytest.fixture(autouse=True)
def disable_selectinload(monkeypatch):
    # Prevent SQLAlchemy mapper/introspection during unit tests that mock DB.execute
    # Replace selectinload with a lightweight object and make `select()` return
    # a dummy selectable that accepts `.options()` and `.where()` without SQLAlchemy coercion.
    monkeypatch.setattr("app.services.order.selectinload", lambda *a, **k: _NoOpLoad())

    class _DummySelectable:
        def options(self, *opts, **kw):
            return self

        def where(self, *args, **kw):
            return self

    monkeypatch.setattr("app.services.order.select", lambda *a, **k: _DummySelectable())


class DummyResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class DummyDB:
    def __init__(self, execute_result=None, get_map=None):
        self._execute_result = execute_result
        self._get_map = get_map or {}

    async def execute(self, stmt):
        await asyncio.sleep(0)
        return self._execute_result

    async def get(self, model, key):
        await asyncio.sleep(0)
        return self._get_map.get((model, key))


def make_product(id=None, price_cents=1000, name="Prod", images=None, sku="SKU"):
    return SimpleNamespace(
        id=id or uuid4(),
        price_cents=price_cents,
        name=name,
        images=images or [],
        sku=sku,
    )


def make_cart_item(product=None, quantity=1, id=None, variant_id=None):
    return SimpleNamespace(
        id=id or uuid4(), product=product, quantity=quantity, variant_id=variant_id
    )


def make_cart(
    items, currency="USD", id=None, user_id=None, session_id=None, status=None
):
    return SimpleNamespace(
        id=id or uuid4(),
        items=items,
        currency=currency,
        user_id=user_id,
        session_id=session_id,
        status=status,
    )


@pytest.mark.asyncio
async def test_preview_order_basic_without_promo():
    p1 = make_product(price_cents=1500, images=["/img.jpg"], sku="SKU1")
    p2 = make_product(price_cents=500, images=[], sku="SKU2")
    ci1 = make_cart_item(product=p1, quantity=2)
    ci2 = make_cart_item(product=p2, quantity=1)
    cart = make_cart(items=[ci1, ci2])

    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    res = await svc.preview_order(cart.id)

    expected_subtotal = 2 * 1500 + 1 * 500
    expected_tax = int((expected_subtotal - 0) * config.TAX_RATE)
    expected_total = expected_subtotal + expected_tax

    assert res["subtotal_cents"] == expected_subtotal
    assert res["discount_cents"] == 0
    assert res["tax_cents"] == expected_tax
    assert res["total_cents"] == expected_total
    assert len(res["items"]) == 2


@pytest.mark.asyncio
async def test_preview_order_with_promo(monkeypatch):
    p = make_product(price_cents=1000)
    ci = make_cart_item(product=p, quantity=3)
    cart = make_cart(items=[ci])

    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    async def fake_validate(self, code, subtotal, user_id=None):
        return {
            "discount_cents": 500,
            "snapshot": {"note": "ok"},
            "promo": SimpleNamespace(id=1),
        }

    monkeypatch.setattr(PromoService, "validate_and_compute", fake_validate)

    res = await svc.preview_order(cart.id, promo_code="SAVE")

    expected_subtotal = 3 * 1000
    expected_discount = 500
    expected_tax = int((expected_subtotal - expected_discount) * config.TAX_RATE)
    expected_total = expected_subtotal - expected_discount + expected_tax

    assert res["subtotal_cents"] == expected_subtotal
    assert res["discount_cents"] == expected_discount
    assert res["applied_discounts_snapshot"]["note"] == "ok"
    assert res["tax_cents"] == expected_tax
    assert res["total_cents"] == expected_total


@pytest.mark.asyncio
async def test_preview_order_empty_cart_raises():
    cart = make_cart(items=[])
    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.preview_order(cart.id)


@pytest.mark.asyncio
async def test_preview_order_missing_cart_raises():
    db = DummyDB(execute_result=DummyResult(None))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.preview_order(uuid4())


@pytest.mark.asyncio
async def test_preview_order_missing_product_raises():
    ci = make_cart_item(product=None)
    cart = make_cart(items=[ci])
    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.preview_order(cart.id)


@pytest.mark.asyncio
async def test_create_order_idempotency_returns_existing():
    # when idempotency key present and order exists, should return it
    existing = SimpleNamespace(id=uuid4(), items=[])
    db = DummyDB(execute_result=DummyResult(existing))
    svc = OrderService(db=cast(AsyncSession, db))

    res = await svc.create_order_from_cart(
        cart_id=uuid4(),
        shipping_address_id=uuid4(),
        user_id=uuid4(),
        idempotency_key="key-123",
    )
    assert res == existing


@pytest.mark.asyncio
async def test_create_order_cart_not_found_raises():
    db = DummyDB(execute_result=DummyResult(None))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.create_order_from_cart(
            cart_id=uuid4(), shipping_address_id=uuid4(), user_id=uuid4()
        )


@pytest.mark.asyncio
async def test_create_order_cart_belongs_to_other_user_raises():
    cart = make_cart(items=[make_cart_item(product=make_product())], user_id=uuid4())
    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.create_order_from_cart(
            cart_id=cart.id, shipping_address_id=uuid4(), user_id=uuid4()
        )


@pytest.mark.asyncio
async def test_create_order_cart_not_active_raises():
    # use simple object with .value to mimic enum-like status used in error message
    cart = make_cart(
        items=[make_cart_item(product=make_product())],
        status=SimpleNamespace(value="completed"),
    )
    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.create_order_from_cart(
            cart_id=cart.id, shipping_address_id=uuid4(), user_id=cart.user_id
        )


@pytest.mark.asyncio
async def test_create_order_empty_cart_raises():
    # ensure status is active so we reach the empty-cart check
    cart = make_cart(items=[], status=SimpleNamespace(value="active"))
    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.create_order_from_cart(
            cart_id=cart.id, shipping_address_id=uuid4(), user_id=cart.user_id
        )


@pytest.mark.asyncio
async def test_create_order_missing_product_in_item_raises():
    # ensure status is active so we reach the missing-product check
    ci = make_cart_item(product=None)
    cart = make_cart(items=[ci], status=SimpleNamespace(value="active"))
    db = DummyDB(execute_result=DummyResult(cart))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.create_order_from_cart(
            cart_id=cart.id, shipping_address_id=uuid4(), user_id=cart.user_id
        )
