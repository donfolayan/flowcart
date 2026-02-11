from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.services import product as product_svc


class DummyResult:
    def __init__(self, scalars_all=None, one_or_none=None):
        self._scalars_all = scalars_all or []
        self._one_or_none = one_or_none

    def scalars(self):
        class Sc:
            def __init__(self, all_v, one_v):
                self._all = all_v
                self._one = one_v

            def all(self):
                return self._all

            def one_or_none(self):
                return self._one

        return Sc(self._scalars_all, self._one_or_none)


class DummyDB:
    def __init__(self, results):
        # results is an iterator or list of DummyResult to return on successive execute calls
        self._results = list(results)
        self.exec_calls = []
        self.add_calls = []

    async def execute(self, query):
        self.exec_calls.append(query)
        if not self._results:
            return DummyResult()
        return self._results.pop(0)

    def add(self, obj):
        self.add_calls.append(obj)


class FakeVariant:
    def __init__(self, id=None, product_id=None, status=None):
        self.id = id or uuid4()
        self.product_id = product_id
        self.status = status


class FakeProduct:
    def __init__(self, id=None, status="draft"):
        self.id = id or uuid4()
        self.status = status


def _chainable_select_obj():
    return SimpleNamespace(
        where=lambda *a, **k: SimpleNamespace(limit=lambda *a, **k: None)
    )


class _EqField:
    def __init__(self):
        pass

    def __eq__(self, other):
        # return an opaque marker used by fake select; the select() mock ignores it
        return "EQ_EXPR"


@pytest.mark.asyncio
async def test_attach_existing_variants_success():
    # Arrange
    ids = [uuid4(), uuid4()]
    found = [
        SimpleNamespace(id=ids[0], product_id=None),
        SimpleNamespace(id=ids[1], product_id=None),
    ]
    db = DummyDB([DummyResult(scalars_all=found), DummyResult()])

    # Monkeypatch module-level SQL builder names to no-ops so no SQLAlchemy runs
    product_svc.select = lambda *a, **k: _chainable_select_obj()
    product_svc.update = lambda *a, **k: SimpleNamespace(
        where=lambda *a, **k: SimpleNamespace(values=lambda **v: "UPDATED")
    )

    prod = FakeProduct(status="active")

    # Act
    await product_svc._attach_existing_variants(db, prod, ids)

    # Assert: two execute calls (select then update)
    assert len(db.exec_calls) == 2


@pytest.mark.asyncio
async def test_attach_existing_variants_missing_raises():
    ids = [uuid4(), uuid4()]
    # only one found
    found = [SimpleNamespace(id=ids[0], product_id=None)]
    db = DummyDB([DummyResult(scalars_all=found)])

    product_svc.select = lambda *a, **k: _chainable_select_obj()

    prod = FakeProduct()

    with pytest.raises(Exception) as exc:
        await product_svc._attach_existing_variants(db, prod, ids)

    assert "Some variants not found" in str(exc.value)


@pytest.mark.asyncio
async def test_attach_existing_variants_conflict_raises():
    ids = [uuid4()]
    # found variant already associated
    found = [SimpleNamespace(id=ids[0], product_id=uuid4())]
    db = DummyDB([DummyResult(scalars_all=found)])

    product_svc.select = lambda *a, **k: _chainable_select_obj()

    prod = FakeProduct()

    with pytest.raises(Exception) as exc:
        await product_svc._attach_existing_variants(db, prod, ids)

    assert "already associated" in str(exc.value)


@pytest.mark.asyncio
async def test_create_inline_variants_creates_and_adds():
    # Arrange
    prod = FakeProduct(status="draft")
    variants_in = [
        {"sku": "A1", "price": 100},
        {"sku": "B2", "price": 200, "id": uuid4()},
    ]

    # Replace ProductVariant in module with a fake class that records kwargs
    class PV:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    product_svc.ProductVariant = PV

    # DB just needs add method
    class LocalDB:
        def __init__(self):
            self.add_calls = []

        def add(self, obj):
            self.add_calls.append(obj)

    db = LocalDB()

    # Act
    created = await product_svc._create_inline_variants(db, prod, variants_in)

    # Assert
    assert len(created) == 2
    assert all(hasattr(c, "product_id") for c in created)
    # ensure db.add was called for both
    assert len(db.add_calls) == 2


@pytest.mark.asyncio
async def test_product_has_variants_true_false():
    prod_id = uuid4()
    # True case
    db_true = DummyDB([DummyResult(one_or_none=SimpleNamespace())])
    product_svc.select = lambda *a, **k: _chainable_select_obj()
    # Ensure ProductVariant.product_id supports equality expression evaluation
    product_svc.ProductVariant = SimpleNamespace(product_id=_EqField())
    assert await product_svc._product_has_variants(db_true, prod_id) is True

    # False case
    db_false = DummyDB([DummyResult(one_or_none=None)])
    product_svc.select = lambda *a, **k: _chainable_select_obj()
    product_svc.ProductVariant = SimpleNamespace(product_id=_EqField())
    assert await product_svc._product_has_variants(db_false, prod_id) is False
