import pytest
from typing import Any, List
from uuid import uuid4
from datetime import datetime, timezone

from fastapi import HTTPException, Response

from app.enums.order_enums import OrderStatusEnum
from app.schemas.order import OrderCreate


class StubOrder:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", uuid4())
        self.cart_id = kwargs.get("cart_id", uuid4())
        self.user_id = kwargs.get("user_id")
        self.session_id = kwargs.get("session_id")
        self.currency = kwargs.get("currency", "USD")
        self.subtotal_cents = kwargs.get("subtotal_cents", 1000)
        self.tax_cents = kwargs.get("tax_cents", 0)
        self.discount_cents = kwargs.get("discount_cents", 0)
        self.total_cents = kwargs.get("total_cents", 1000)
        self.shipping_address_id = kwargs.get("shipping_address_id")
        self.billing_address_id = kwargs.get("billing_address_id")
        self.billing_address_same_as_shipping = kwargs.get(
            "billing_address_same_as_shipping", True
        )
        self.status = kwargs.get("status", OrderStatusEnum.PENDING)
        self.created_at = kwargs.get("created_at", datetime.now(timezone.utc))
        self.updated_at = kwargs.get("updated_at", datetime.now(timezone.utc))
        self.placed_at = kwargs.get("placed_at")
        self.paid_at = kwargs.get("paid_at")
        self.fulfilled_at = kwargs.get("fulfilled_at")
        self.canceled_at = kwargs.get("canceled_at")
        self.version = kwargs.get("version", 1)
        self.items: List[Any] = kwargs.get("items", [])


class DummyResult:
    def __init__(self, obj=None):
        self._obj = obj

    def scalar_one_or_none(self):
        return self._obj

    def scalars(self):
        class S:
            def __init__(self, obj):
                self._obj = obj

            def all(self):
                return [self._obj] if self._obj is not None else []

        return S(self._obj)


class FakeDB:
    def __init__(self, execute_result=None, commit_raises=None):
        self.execute_result = execute_result
        self.commit_raises = commit_raises
        self.committed = False

    async def execute(self, stmt):
        return DummyResult(self.execute_result)

    async def commit(self):
        if self.commit_raises:
            raise self.commit_raises
        self.committed = True

    async def rollback(self):
        return None


@pytest.mark.asyncio
async def test_create_order_from_cart_success(monkeypatch):
    from app.api.v1.routes import order as order_routes

    # stub OrderService
    class StubService:
        def __init__(self, db):
            self.db = db

        async def create_order_from_cart(self, **kwargs):
            return StubOrder(cart_id=kwargs.get("cart_id"))

    monkeypatch.setattr(order_routes, "OrderService", StubService)

    payload = OrderCreate(
        cart_id=uuid4(),
        shipping_address_id=uuid4(),
        billing_address_id=None,
        billing_address_same_as_shipping=True,
        idempotency_key=None,
        promo_code=None,
    )

    fake_db = FakeDB()

    res = await order_routes.create_order_from_cart(
        payload,
        Response(),
        None,
        "sess",
        fake_db,  # type: ignore
    )

    assert hasattr(res, "id")
    assert res.cart_id == payload.cart_id


@pytest.mark.asyncio
async def test_preview_order_success(monkeypatch):
    from app.api.v1.routes import order as order_routes

    class StubService:
        def __init__(self, db):
            self.db = db

        async def preview_order(self, **kwargs):
            return {
                "subtotal_cents": 1000,
                "discount_cents": 0,
                "tax_cents": 0,
                "total_cents": 1000,
                "items": [],
            }

    monkeypatch.setattr(order_routes, "OrderService", StubService)

    payload = OrderCreate(
        cart_id=uuid4(),
        shipping_address_id=uuid4(),
        billing_address_id=None,
        billing_address_same_as_shipping=True,
        idempotency_key=None,
        promo_code=None,
    )
    fake_db = FakeDB()

    res = await order_routes.preview_order(payload, None, fake_db)  # type: ignore

    assert res.total_cents == 1000


@pytest.mark.asyncio
async def test_get_order_session_forbidden():
    from app.api.v1.routes import order as order_routes

    # Create order with different session
    order = StubOrder(session_id="other-session")
    fake_db = FakeDB(execute_result=order)

    with pytest.raises(HTTPException) as exc:
        await order_routes.get_order(order.id, None, "my-session", fake_db)  # type: ignore

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_cancel_order_success_and_not_found():
    from app.api.v1.routes import order as order_routes

    # Not found case
    fake_db_none = FakeDB(execute_result=None)
    with pytest.raises(HTTPException) as exc:
        await order_routes.cancel_order(uuid4(), None, "sess", fake_db_none)  # type: ignore
    assert exc.value.status_code == 404

    # Success cancel
    order = StubOrder(session_id="sess", status=OrderStatusEnum.PENDING)
    fake_db = FakeDB(execute_result=order)

    await order_routes.cancel_order(order.id, None, "sess", fake_db)  # type: ignore

    assert order.status == OrderStatusEnum.CANCELLED
    assert fake_db.committed


def test_import_order_routes():
    import app.api.v1.routes.order as ord_mod

    assert hasattr(ord_mod, "router")
