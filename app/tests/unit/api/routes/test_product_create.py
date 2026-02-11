import pytest

from uuid import uuid4
from typing import cast
from datetime import datetime, timezone
from types import SimpleNamespace
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from fastapi import Response

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
                return self._v if isinstance(self._v, list) else [self._v]

            def one(self):
                return self._v

            def one_or_none(self):
                return self._v

            def first(self):
                if self._v is None:
                    return None
                if isinstance(self._v, list):
                    return self._v[0] if self._v else None
                return self._v

        return S(self._vals)


class FakeDB:
    def __init__(self, execute_result=None):
        self._execute_result = execute_result
        self.added = []
        self.last_query = None
        self.flushed = False
        self.committed = False
        self.rolled_back = False

    async def execute(self, q):
        # record the last query to assert delete/select behavior
        self.last_query = q
        return self._execute_result

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True

    async def rollback(self):
        self.rolled_back = True


class DummyLoad:
    def selectinload(self, *args, **kwargs):
        return self


class DummySelect:
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


class DummyCol:
    def __init__(self, name=None):
        self.name = name

    def __getattr__(self, item):
        return self

    def __call__(self, *a, **k):
        return self

    def __eq__(self, other):
        return False

    def __repr__(self):
        return f"<DummyCol {self.name}>"


@pytest.mark.asyncio
async def test_create_product_success(monkeypatch):
    # Prepare payload
    payload = ProductCreate.model_validate(
        {
            "name": "prod",
            "slug": "prod",
            "is_variable": False,
            "base_price": 100,
        }
    )
    resp = Response()

    # Monkeypatch Product to avoid SQLAlchemy mapped class
    def prod_factory(**kwargs):
        base = dict(kwargs)
        base.setdefault("variants", [])
        base.setdefault("status", "draft")
        base.setdefault("is_variable", False)
        base.setdefault("created_at", datetime.now(timezone.utc))
        base.setdefault("updated_at", datetime.now(timezone.utc))
        base.setdefault("id", uuid4())
        return SimpleNamespace(**base)

    monkeypatch.setattr(product_routes, "Product", prod_factory)
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    monkeypatch.setattr(product_routes, "delete", lambda *a, **k: DummySelect())
    # ensure attribute access like Product.id and Product.variants doesn't fail
    prod_factory.id = DummyCol("id")  # type: ignore[attr-defined]
    prod_factory.variants = DummyCol("variants")  # type: ignore[attr-defined]
    monkeypatch.setattr(
        product_routes,
        "ProductVariant",
        SimpleNamespace(media_associations=DummyCol("media_associations")),
    )
    monkeypatch.setattr(
        product_routes,
        "ProductMedia",
        SimpleNamespace(media=DummyCol("media"), product_id=DummyCol("product_id")),
    )

    # After final select, return the added product
    fake_product = prod_factory(name="prod", slug="prod")
    fake_db = FakeDB(execute_result=DummyRes(fake_product))

    result = await product_routes.create_product(
        payload, resp, db=cast(AsyncSession, fake_db)
    )
    assert result.id == fake_product.id
    assert resp.headers["Location"].startswith("/products/")


@pytest.mark.asyncio
async def test_create_product_media_clear_calls_delete(monkeypatch):
    payload = ProductCreate.model_validate(
        {
            "name": "p2",
            "slug": "p2",
            "is_variable": False,
            "base_price": 50,
            "media": [],
        }
    )
    resp = Response()

    def prod_factory(**kwargs):
        base = dict(kwargs)
        base.setdefault("variants", [])
        base.setdefault("status", "draft")
        base.setdefault("is_variable", False)
        base.setdefault("created_at", datetime.now(timezone.utc))
        base.setdefault("updated_at", datetime.now(timezone.utc))
        base.setdefault("id", uuid4())
        return SimpleNamespace(**base)

    monkeypatch.setattr(product_routes, "Product", prod_factory)
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    monkeypatch.setattr(product_routes, "delete", lambda *a, **k: DummySelect())
    prod_factory.id = DummyCol("id")  # type: ignore[attr-defined]
    prod_factory.variants = DummyCol("variants")  # type: ignore[attr-defined]
    monkeypatch.setattr(
        product_routes,
        "ProductVariant",
        SimpleNamespace(media_associations=DummyCol("media_associations")),
    )
    monkeypatch.setattr(
        product_routes,
        "ProductMedia",
        SimpleNamespace(media=DummyCol("media"), product_id=DummyCol("product_id")),
    )

    fake_product = prod_factory(name="p2", slug="p2")
    fake_db = FakeDB(execute_result=DummyRes(fake_product))

    await product_routes.create_product(payload, resp, db=cast(AsyncSession, fake_db))
    # media=[] should have executed a delete(ProductMedia) call
    assert fake_db.last_query is not None


@pytest.mark.asyncio
async def test_create_product_calls_validate_media_and_add(monkeypatch):
    payload = ProductCreate.model_validate(
        {
            "name": "p3",
            "slug": "p3",
            "is_variable": False,
            "base_price": 20,
            "media": [uuid4()],
        }
    )
    resp = Response()

    called = {"ok": False}

    async def fake_validate(db, product, media_ids):
        called["ok"] = True

    def prod_factory(**kwargs):
        base = dict(kwargs)
        base.setdefault("variants", [])
        base.setdefault("status", "draft")
        base.setdefault("is_variable", False)
        base.setdefault("created_at", datetime.now(timezone.utc))
        base.setdefault("updated_at", datetime.now(timezone.utc))
        base.setdefault("id", uuid4())
        return SimpleNamespace(**base)

    monkeypatch.setattr(product_routes, "Product", prod_factory)
    monkeypatch.setattr(product_routes, "_validate_media_and_add", fake_validate)
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    monkeypatch.setattr(product_routes, "delete", lambda *a, **k: DummySelect())
    prod_factory.id = DummyCol("id")  # type: ignore[attr-defined]
    prod_factory.variants = DummyCol("variants")  # type: ignore[attr-defined]
    monkeypatch.setattr(
        product_routes,
        "ProductVariant",
        SimpleNamespace(media_associations=DummyCol("media_associations")),
    )
    monkeypatch.setattr(
        product_routes,
        "ProductMedia",
        SimpleNamespace(media=DummyCol("media"), product_id=DummyCol("product_id")),
    )

    fake_product = prod_factory(name="p3", slug="p3")
    fake_db = FakeDB(execute_result=DummyRes(fake_product))

    await product_routes.create_product(payload, resp, db=cast(AsyncSession, fake_db))
    assert called["ok"] is True


@pytest.mark.asyncio
async def test_create_product_slug_retry_on_integrity_error(monkeypatch):
    """Simulate an IntegrityError on first commit to trigger slug retry logic."""
    payload = ProductCreate.model_validate(
        {
            "name": "p-slug",
            "slug": "p-slug",
            "is_variable": False,
            "base_price": 10,
        }
    )
    resp = Response()

    # prepare a single mutable product instance that will be returned by Product()
    fake_product = SimpleNamespace(
        name="p-slug",
        slug="p-slug",
        variants=[],
        status="draft",
        is_variable=False,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        id=uuid4(),
    )

    # product factory returns the same fake_product instance so route can update slug on retry
    def prod_factory(**kwargs):
        return fake_product

    # Fake DB that raises IntegrityError on first commit, then succeeds
    class FakeDBCommitOnce(FakeDB):
        def __init__(self, execute_result=None):
            super().__init__(execute_result=execute_result)
            self._commit_calls = 0

        async def commit(self):
            if self._commit_calls == 0:
                self._commit_calls += 1
                raise IntegrityError(
                    "slug unique constraint", None, Exception("slug unique")
                )
            self.committed = True

        async def rollback(self):
            # track rollback calls as before
            self.rolled_back = True

    monkeypatch.setattr(product_routes, "Product", prod_factory)
    monkeypatch.setattr(product_routes, "selectinload", lambda *a, **k: DummyLoad())
    monkeypatch.setattr(product_routes, "select", lambda *a, **k: DummySelect())
    monkeypatch.setattr(product_routes, "delete", lambda *a, **k: DummySelect())
    prod_factory.id = DummyCol("id")  # type: ignore[attr-defined]
    prod_factory.variants = DummyCol("variants")  # type: ignore[attr-defined]
    monkeypatch.setattr(
        product_routes,
        "ProductVariant",
        SimpleNamespace(media_associations=DummyCol("media_associations")),
    )
    monkeypatch.setattr(
        product_routes,
        "ProductMedia",
        SimpleNamespace(media=DummyCol("media"), product_id=DummyCol("product_id")),
    )

    fake_db = FakeDBCommitOnce(execute_result=DummyRes(fake_product))

    result = await product_routes.create_product(
        payload, resp, db=cast(AsyncSession, fake_db)
    )

    # The route should have retried and modified the slug (base prefix before last '-' preserved)
    assert result.slug is not None
    assert result.slug != "p-slug"
    assert result.slug.startswith("p-")
