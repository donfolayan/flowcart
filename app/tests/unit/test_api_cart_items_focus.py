import pytest
from uuid import uuid4
from types import SimpleNamespace
from datetime import datetime, timezone
from fastapi import Response, HTTPException
from sqlalchemy.exc import IntegrityError
from decimal import Decimal

from app.api.routes import cart_items as cart_routes


class FakeModel(SimpleNamespace):
    """SimpleNamespace with model_dump() for Pydantic compatibility in tests."""
    def model_dump(self):
        return vars(self)


class DummyRes:
    def __init__(self, vals):
        self._vals = vals

    def scalars(self):
        class S:
            def __init__(self, v):
                self._v = v

            def one_or_none(self):
                return self._v

            def all(self):
                return self._v

        return S(self._vals)


class FakeDB:
    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.deleted = []
        self.committed = False

    async def execute(self, q):
        if self._results:
            return self._results.pop(0)
        return DummyRes(None)

    async def rollback(self):
        return None

    async def commit(self):
        self.committed = True

    async def delete(self, obj):
        self.deleted.append(obj)


class DummySelect:
    def __init__(self, *a, **k):
        pass

    def options(self, *a, **k):
        return self

    def where(self, *a, **k):
        return self


@pytest.mark.asyncio
async def test_add_item_to_cart_success(monkeypatch):
    fake_cart = SimpleNamespace(
        id=uuid4(),
        status="active",
        total=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        version=1,
        items=[],
    )

    # avoid SQLAlchemy loader inspection
    # use real selectinload so options() receives a valid execution option
    # (we avoid creating model instances in the test so mapper init won't run)
    monkeypatch.setattr(cart_routes, "select", lambda *a, **k: DummySelect(*a, **k))
    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "select", DummySelect)

    # monkeypatch get_cart_or_404 to return our fake cart
    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    # monkeypatch add service to be a no-op
    async def _fake_add(**kwargs):
        return None

    monkeypatch.setattr(cart_routes, "_add_item_to_cart", _fake_add)

    fake_db = FakeDB(execute_results=[DummyRes(fake_cart)])

    payload = FakeModel(variant_id=None, product_id=uuid4(), quantity=1)
    resp = Response()

    result = await cart_routes.add_item_to_cart(fake_cart.id, payload, resp, db=fake_db)  # type: ignore

    assert resp.headers.get("Location") == f"/cart/{fake_cart.id}"
    assert result is not None


@pytest.mark.asyncio
async def test_add_item_to_cart_non_active_cart(monkeypatch):
    fake_cart = SimpleNamespace(id=uuid4(), status="archived")

    monkeypatch.setattr(cart_routes, "select", DummySelect)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    fake_db = FakeDB()
    payload = FakeModel(variant_id=None, product_id=uuid4(), quantity=1)
    resp = Response()

    with pytest.raises(HTTPException) as exc:
        await cart_routes.add_item_to_cart(fake_cart.id, payload, resp, db=fake_db)  # type: ignore

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_patch_cart_items_not_found(monkeypatch):
    fake_cart = SimpleNamespace(id=uuid4(), status="active")

    monkeypatch.setattr(cart_routes, "select", DummySelect)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    fake_db = FakeDB(execute_results=[DummyRes(None)])

    payload = FakeModel(quantity=2)

    with pytest.raises(HTTPException) as exc:
        await cart_routes.patch_cart_items(fake_cart.id, uuid4(), payload, db=fake_db)  # type: ignore

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_cart_items_success(monkeypatch):
    now = datetime.now(timezone.utc)
    fake_cart_item = SimpleNamespace(id=uuid4(), cart_id=uuid4(), quantity=1)
    fake_cart = SimpleNamespace(
        id=uuid4(),
        status="active",
        total=0,
        created_at=now,
        updated_at=now,
        version=1,
        items=[],
    )

    monkeypatch.setattr(cart_routes, "selectinload", lambda *a, **k: None)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    async def _fake_update(**kwargs):
        return None

    monkeypatch.setattr(cart_routes, "_update_cart_item", _fake_update)

    # first execute returns the cart_item, second returns the refreshed cart
    fake_db = FakeDB(execute_results=[DummyRes(fake_cart_item), DummyRes(fake_cart)])
    payload = cart_routes.CartItemUpdate(
        quantity=3,
    )
    res = await cart_routes.patch_cart_items(
        fake_cart.id,
        fake_cart_item.id,
        payload,
        db=fake_db,  # type: ignore
    )
    assert res is not None
    assert res is not None


@pytest.mark.asyncio
async def test_add_item_to_cart_integrity_error(monkeypatch):
    fake_cart = SimpleNamespace(id=uuid4(), status="active")

    # stub select/selectinload to avoid SQLAlchemy mapper checks
    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "selectinload", lambda *a, **k: None)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    async def _bad_add(**kwargs):
        raise IntegrityError("", {}, Exception("orig"))

    monkeypatch.setattr(cart_routes, "_add_item_to_cart", _bad_add)

    fake_db = FakeDB(execute_results=[DummyRes(None)])
    payload = FakeModel(variant_id=None, product_id=uuid4(), quantity=1)
    resp = Response()

    with pytest.raises(HTTPException) as exc:
        await cart_routes.add_item_to_cart(fake_cart.id, payload, resp, db=fake_db)  # type: ignore

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_item_to_cart_reload_not_found(monkeypatch):
    fake_cart = SimpleNamespace(id=uuid4(), status="active")
    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "selectinload", lambda *a, **k: None)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    async def _fake_add(**kwargs):
        return None

    monkeypatch.setattr(cart_routes, "_add_item_to_cart", _fake_add)

    # simulate reload returning no cart
    fake_db = FakeDB(execute_results=[DummyRes(None)])
    payload = FakeModel(variant_id=None, product_id=uuid4(), quantity=1)
    resp = Response()

    with pytest.raises(HTTPException) as exc:
        await cart_routes.add_item_to_cart(fake_cart.id, payload, resp, db=fake_db)  # type: ignore

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_patch_cart_items_integrity_error(monkeypatch):
    fake_cart_item = SimpleNamespace(id=uuid4(), cart_id=uuid4(), quantity=1)
    fake_cart = SimpleNamespace(id=uuid4(), status="active")

    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "selectinload", lambda *a, **k: None)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    async def _bad_update(**kwargs):
        raise IntegrityError("", {}, Exception("orig"))

    monkeypatch.setattr(cart_routes, "_update_cart_item", _bad_update)

    fake_db = FakeDB(execute_results=[DummyRes(fake_cart_item)])

    payload = FakeModel(quantity=3)

    with pytest.raises(HTTPException) as exc:
        await cart_routes.patch_cart_items(
            fake_cart.id,
            fake_cart_item.id,
            payload,  # type: ignore
            db=fake_db,  # type: ignore
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_cart_item_not_found_and_success(monkeypatch):
    fake_cart = SimpleNamespace(id=uuid4(), version=1)

    monkeypatch.setattr(cart_routes, "select", DummySelect)
    monkeypatch.setattr(cart_routes, "selectinload", lambda *a, **k: None)

    async def _fake_get(cart_id, db):
        return fake_cart

    monkeypatch.setattr(cart_routes, "get_cart_or_404", _fake_get)

    # case: not found
    fake_db = FakeDB(execute_results=[DummyRes(None)])
    with pytest.raises(HTTPException) as exc:
        await cart_routes.delete_cart_item(fake_cart.id, uuid4(), db=fake_db)  # type: ignore
    assert exc.value.status_code == 404

    # case: success
    cart_item = SimpleNamespace(id=uuid4())
    fake_db = FakeDB(execute_results=[DummyRes(cart_item)])
    resp = await cart_routes.delete_cart_item(fake_cart.id, cart_item.id, db=fake_db)  # type: ignore
    # ensure item was deleted and commit called
    assert cart_item in fake_db.deleted
    assert fake_cart.version == 2
    assert resp.status_code == 204
