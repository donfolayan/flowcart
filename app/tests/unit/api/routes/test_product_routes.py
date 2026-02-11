import pytest

from datetime import datetime, timezone
from typing import cast
from uuid import uuid4
from fastapi import HTTPException, Response
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes import product as product_routes
from app.schemas.product import ProductCreate


class DummyRes:
    def __init__(self, vals):
        self._vals = vals

    def scalars(self):
        class S:
            def __init__(self, v):
                self._v = v

            def all(self):
                # if underlying is a list, return it
                return self._v if isinstance(self._v, list) else [self._v]

            def first(self):
                if self._v is None:
                    return None
                if isinstance(self._v, list):
                    return self._v[0] if self._v else None
                return self._v

            def one(self):
                return self.first()

            def one_or_none(self):
                return self.first()

        return S(self._vals)


class FakeDB:
    def __init__(self, execute_result=None):
        self._execute_result = execute_result
        self.added = []
        self.deleted = []
        self.committed = False
        self.rolled_back = False

    async def execute(self, q):
        return self._execute_result

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        return None

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True

    async def delete(self, obj):
        self.deleted.append(obj)


class DummyLoad:
    def selectinload(self, *args, **kwargs):
        return self


class DummySelect:
    def __init__(self):
        self._where = None

    def options(self, *args, **kwargs):
        return self

    def offset(self, *args, **kwargs):
        return self

    def limit(self, *args, **kwargs):
        return self

    def order_by(self, *args, **kwargs):
        return self

    def where(self, *args, **kwargs):
        return self


@pytest.mark.asyncio
async def test_get_product_by_id_not_found(monkeypatch):
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    fake_db = FakeDB(execute_result=DummyRes(None))
    with pytest.raises(HTTPException) as exc:
        await product_routes.get_product_by_id(uuid4(), db=cast(AsyncSession, fake_db))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_get_product_by_id_found(monkeypatch):
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    p = SimpleNamespace(
        id=uuid4(),
        name="X",
        slug="x",
        variants=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    fake_db = FakeDB(execute_result=DummyRes(p))
    res = await product_routes.get_product_by_id(p.id, db=cast(AsyncSession, fake_db))
    assert res.id == p.id


@pytest.mark.asyncio
async def test_list_all_products_returns_list(monkeypatch):
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    p = SimpleNamespace(
        id=uuid4(),
        name="Y",
        slug="y",
        variants=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    fake_db = FakeDB(execute_result=DummyRes([p]))
    res = await product_routes.list_all_products(
        skip=0, limit=10, db=cast(AsyncSession, fake_db)
    )
    assert isinstance(res, list)
    assert res[0].id == p.id


@pytest.mark.asyncio
async def test_create_product_missing_base_price_raises():
    payload = ProductCreate.model_validate(
        {"name": "no-price", "slug": "no-price", "is_variable": False}
    )
    resp = Response()
    fake_db = FakeDB()
    with pytest.raises(HTTPException) as exc:
        await product_routes.create_product(
            payload, resp, db=cast(AsyncSession, fake_db)
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_create_product_variable_active_without_variants_raises():
    payload = ProductCreate.model_validate(
        {"name": "v", "slug": "v", "is_variable": True, "status": "active"}
    )
    resp = Response()
    fake_db = FakeDB()
    with pytest.raises(HTTPException) as exc:
        await product_routes.create_product(
            payload, resp, db=cast(AsyncSession, fake_db)
        )
    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_delete_product_not_found(monkeypatch):
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    fake_db = FakeDB(execute_result=DummyRes(None))
    with pytest.raises(HTTPException) as exc:
        await product_routes.delete_product(uuid4(), db=cast(AsyncSession, fake_db))
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_delete_product_success(monkeypatch):
    p = SimpleNamespace(id=uuid4())
    fake_db = FakeDB(execute_result=DummyRes(p))

    committed = {"ok": False}

    async def fake_commit():
        committed["ok"] = True

    fake_db.commit = fake_commit

    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    await product_routes.delete_product(p.id, db=cast(AsyncSession, fake_db))
    assert committed["ok"] is True
