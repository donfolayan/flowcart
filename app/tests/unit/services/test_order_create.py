import asyncio
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order import OrderService
from app.models.address import Address
from app.enums.cart_enums import CartStatus
from app.core.config import config


class DummyExec:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value

    def scalars(self):
        class S:
            def __init__(self, v):
                self.v = v

            def one_or_none(self):
                return self.v

        return S(self._value)


class DummyDB:
    def __init__(self, execute_result=None, get_map=None):
        self._execute_result = execute_result
        self._get_map = get_map or {}
        self.added = []

    async def execute(self, stmt):
        await asyncio.sleep(0)
        return self._execute_result

    async def get(self, model, key):
        await asyncio.sleep(0)
        return self._get_map.get((model, key))

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        await asyncio.sleep(0)

    async def commit(self):
        await asyncio.sleep(0)

    async def refresh(self, obj):
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def noop_sqlalchemy(monkeypatch):
    # Avoid SQLAlchemy load/inspect behavior in unit tests
    class _NoOpLoad:
        def selectinload(self, *a, **k):
            return self

    monkeypatch.setattr("app.services.order.selectinload", lambda *a, **k: _NoOpLoad())

    class DummySel:
        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr("app.services.order.select", lambda *a, **k: DummySel())


def make_product(price_cents=1000, images=None):
    return SimpleNamespace(
        id=uuid4(), price_cents=price_cents, name="P", images=images or [], sku="S"
    )


def make_cart(items, status=CartStatus.ACTIVE):
    return SimpleNamespace(
        id=uuid4(),
        items=items,
        currency="USD",
        user_id=None,
        session_id=None,
        status=status,
    )


@pytest.mark.asyncio
async def test_create_order_idempotency_returns_existing():
    existing = SimpleNamespace(id=uuid4(), items=[])
    db = DummyDB(execute_result=DummyExec(existing))
    svc = OrderService(db=cast(AsyncSession, db))

    res = await svc.create_order_from_cart(
        cart_id=uuid4(),
        shipping_address_id=uuid4(),
        idempotency_key="k",
        session_id="s",
    )
    assert res is existing


@pytest.mark.asyncio
async def test_create_order_missing_cart_raises():
    db = DummyDB(execute_result=DummyExec(None))
    svc = OrderService(db=cast(AsyncSession, db))

    with pytest.raises(HTTPException):
        await svc.create_order_from_cart(cart_id=uuid4(), shipping_address_id=uuid4())


@pytest.mark.asyncio
async def test_create_order_success_with_promo(monkeypatch):
    # Build cart with items
    prod = make_product(price_cents=2000, images=["/i.jpg"])
    ci = SimpleNamespace(id=uuid4(), product=prod, quantity=2, variant_id=None)
    cart = make_cart([ci])

    # DB execute for cart select should return the cart
    db = DummyDB(execute_result=DummyExec(cart), get_map={(Address, uuid4()): None})

    # Provide shipping address on db.get
    shipping_id = uuid4()
    addr = SimpleNamespace(
        id=shipping_id,
        name="Me",
        company=None,
        line1="1 St",
        line2=None,
        city="C",
        region=None,
        postal_code=None,
        country="US",
        phone=None,
        email=None,
        extra=None,
    )
    db._get_map = {(Address, shipping_id): addr}

    svc = OrderService(db=cast(AsyncSession, db))

    # Monkeypatch promo service validate to give discount and increment to be a noop
    async def fake_validate(self, code, subtotal, user_id=None):
        return {
            "discount_cents": 500,
            "snapshot": {"k": "v"},
            "promo": SimpleNamespace(id=1),
        }

    async def fake_increment(self, promo_id):
        return 1

    monkeypatch.setattr(
        "app.services.order.PromoService.validate_and_compute", fake_validate
    )
    monkeypatch.setattr(
        "app.services.order.PromoService.increment_usage_atomic", fake_increment
    )

    # Patch Order.model_validate to return the object passed in (avoid SQLAlchemy model requirements)
    class FakeOrder:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
            if not getattr(self, "id", None):
                self.id = uuid4()

        @staticmethod
        def model_validate(x):
            return x

    monkeypatch.setattr("app.services.order.Order", FakeOrder)

    class FakeOrderItem:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    monkeypatch.setattr("app.services.order.OrderItem", FakeOrderItem)

    res = await svc.create_order_from_cart(
        cart_id=cart.id, shipping_address_id=shipping_id, promo_code="SAVE"
    )

    assert res.subtotal_cents == 4000
    assert res.discount_cents == 500
    expected_tax = int((4000 - 500) * config.TAX_RATE)
    assert res.tax_cents == expected_tax
    assert res.promo_code == "save"
