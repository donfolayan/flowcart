import asyncio
import uuid
import pytest
from types import SimpleNamespace
from typing import cast
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.order import OrderService
from app.services.promo import PromoService


class DummyDB:
    def __init__(self, cart: object):
        self._cart = cart

    async def execute(self, stmt):
        class Res:
            def __init__(self, value):
                self._v = value

            def scalar_one_or_none(self):
                return self._v

        await asyncio.sleep(0)
        return Res(self._cart)


@pytest.mark.asyncio
async def test_preview_order_basic(monkeypatch):
    # Build a fake cart with items (use real UUIDs to satisfy type checks)
    product_id = uuid.uuid4()
    cart_id = uuid.uuid4()

    product = SimpleNamespace(id=product_id, price_cents=1000, name="Widget")
    cart_item = SimpleNamespace(quantity=2, product=product)
    cart = SimpleNamespace(id=cart_id, items=[cart_item], currency="USD")

    db = DummyDB(cart=cart)

    # Monkeypatch SQLAlchemy helpers used in the service to avoid mapper inspection
    class FakeStmt:
        def options(self, *args, **kwargs):
            return self

        def where(self, *args, **kwargs):
            return self

    monkeypatch.setattr("app.services.order.select", lambda *a, **k: FakeStmt())

    class FakeLoader:
        def selectinload(self, *args, **kwargs):
            return self

    monkeypatch.setattr("app.services.order.selectinload", lambda *a, **k: FakeLoader())

    svc = OrderService(db=cast(AsyncSession, db))

    # Monkeypatch PromoService to not error
    async def fake_validate_and_compute(code, subtotal_cents, user_id=None):
        return {"promo": None, "discount_cents": 0, "snapshot": None}

    monkeypatch.setattr(PromoService, "validate_and_compute", fake_validate_and_compute)

    result = await svc.preview_order(cart_id=cart_id, promo_code=None, user_id=None)
    assert "subtotal_cents" in result
    assert result["subtotal_cents"] == 2000
    assert result["discount_cents"] == 0
    assert result["total_cents"] >= 0
