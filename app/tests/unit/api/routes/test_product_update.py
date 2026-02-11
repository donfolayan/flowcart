import pytest

from uuid import uuid4
from typing import cast
from datetime import datetime, timezone
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import HTTPException

from app.api.routes import product as product_routes
from app.schemas.product import ProductUpdate


class DummyRes:
    def __init__(self, vals):
        self._vals = vals

    def scalars(self):
        class S:
            def __init__(self, v):
                self._v = v

            def all(self):
                return self._v if isinstance(self._v, list) else [self._v]

            def one_or_none(self):
                return self._v

            def first(self):
                if self._v is None:
                    return None
                if isinstance(self._v, list):
                    return self._v[0] if self._v else None
                return self._v

        return S(self._vals)


class FakeDBMulti:
    """Fake DB that returns a sequence of execute results for each execute() call."""

    def __init__(self, execute_results=None):
        self._results = list(execute_results or [])
        self.added = []
        self.last_query = None
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    async def execute(self, q):
        self.last_query = q
        if self._results:
            return self._results.pop(0)
        return None

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def refresh(self, obj):
        # noop for tests
        return None


def make_product(id=None, **overrides):
    id = id or uuid4()
    base = dict(
        name="p",
        slug="p",
        variants=[],
        status="draft",
        is_variable=False,
        base_price=None,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        id=id,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


@pytest.mark.asyncio
async def test_update_product_not_found():
    fake_db = FakeDBMulti(execute_results=[DummyRes(None)])

    payload = ProductUpdate.model_validate({"name": "x"})

    with pytest.raises(HTTPException) as exc:
        await product_routes.update_product(
            uuid4(), payload, db=cast(AsyncSession, fake_db)
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_product_active_variable_requires_variants(monkeypatch):
    # existing product found
    fake_product = make_product()
    fake_db = FakeDBMulti(execute_results=[DummyRes(fake_product)])

    # force _product_has_variants to return False (async)
    async def _fake_has(db, pid):
        return False

    monkeypatch.setattr(product_routes, "_product_has_variants", _fake_has)

    payload = ProductUpdate.model_validate({"status": "active", "is_variable": True})

    with pytest.raises(HTTPException) as exc:
        await product_routes.update_product(
            fake_product.id, payload, db=cast(AsyncSession, fake_db)
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_product_active_variable_price_validation(monkeypatch):
    # existing product found and is variable/active after update
    fake_product = make_product(status="active", is_variable=True)

    # simulate select(Product) then select(ProductVariant)
    variant_missing = SimpleNamespace(id=uuid4(), price=None)
    fake_db = FakeDBMulti(
        execute_results=[DummyRes(fake_product), DummyRes([variant_missing])]
    )

    # provide a variant_ids list so update validation doesn't call _product_has_variants
    payload = ProductUpdate.model_validate({"variant_ids": [uuid4()]})

    with pytest.raises(HTTPException) as exc:
        await product_routes.update_product(
            fake_product.id, payload, db=cast(AsyncSession, fake_db)
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_update_product_media_clear_and_validate(monkeypatch):
    # Test media=[] triggers delete(ProductMedia) execution
    fake_product = make_product()
    # sequence: select(Product) -> delete(ProductMedia) -> select(ProductVariant)
    fake_db = FakeDBMulti(
        execute_results=[DummyRes(fake_product), DummyRes(None), DummyRes([])]
    )

    # ensure delete runs when media = []
    payload = ProductUpdate.model_validate({"media": []})

    await product_routes.update_product(
        fake_product.id, payload, db=cast(AsyncSession, fake_db)
    )
    assert fake_db.last_query is not None


@pytest.mark.asyncio
async def test_update_product_media_calls_validate_and_add(monkeypatch):
    # Test media list triggers _validate_media_and_add
    fake_product = make_product()
    fake_db = FakeDBMulti(execute_results=[DummyRes(fake_product), DummyRes([])])

    called = {"ok": False}

    async def fake_validate(db, product, media_ids):
        called["ok"] = True

    monkeypatch.setattr(product_routes, "_validate_media_and_add", fake_validate)

    payload = ProductUpdate.model_validate({"media": [uuid4()]})

    await product_routes.update_product(
        fake_product.id, payload, db=cast(AsyncSession, fake_db)
    )
    assert called["ok"] is True
