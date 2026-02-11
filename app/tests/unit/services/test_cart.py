import asyncio
from types import SimpleNamespace
from typing import cast
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services import cart as cart_service


class DummyScalar:
    def __init__(self, value):
        self._value = value

    def one_or_none(self):
        return self._value


class DummyExecuteResult:
    def __init__(self, value):
        self._value = value

    def scalars(self):
        return DummyScalar(self._value)

    def scalar_one_or_none(self):
        return self._value


class DummyDB:
    def __init__(self, execute_result=None, get_map=None):
        self._execute_result = execute_result
        self._get_map = get_map or {}
        self.deleted = []
        self.added = []

    async def execute(self, stmt):
        await asyncio.sleep(0)
        return self._execute_result

    async def get(self, model, key):
        await asyncio.sleep(0)
        return self._get_map.get((model, key))

    async def delete(self, obj):
        await asyncio.sleep(0)
        self.deleted.append(obj)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        await asyncio.sleep(0)

    async def commit(self):
        await asyncio.sleep(0)

    async def rollback(self):
        await asyncio.sleep(0)

    async def refresh(self, obj):
        await asyncio.sleep(0)


class DummyDBMulti:
    """DB fake that returns a sequence of execute results for successive execute calls."""

    def __init__(self, execute_results=None, get_map=None):
        self._results = list(execute_results or [])
        self._get_map = get_map or {}
        self.deleted = []
        self.added = []

    async def execute(self, stmt):
        await asyncio.sleep(0)
        if not self._results:
            return DummyExecuteResult(None)
        return self._results.pop(0)

    async def get(self, model, key):
        await asyncio.sleep(0)
        return self._get_map.get((model, key))

    async def delete(self, obj):
        await asyncio.sleep(0)
        self.deleted.append(obj)

    def add(self, obj):
        self.added.append(obj)

    async def flush(self):
        await asyncio.sleep(0)

    async def commit(self):
        await asyncio.sleep(0)

    async def rollback(self):
        await asyncio.sleep(0)

    async def refresh(self, obj):
        await asyncio.sleep(0)


@pytest.fixture(autouse=True)
def disable_sqlalchemy_loads(monkeypatch):
    # avoid SQLAlchemy mapper/options coercion in unit tests
    monkeypatch.setattr("app.services.cart.selectinload", lambda *a, **k: None)

    class _DummySelectable:
        def where(self, *a, **k):
            return self

        def options(self, *a, **k):
            return self

        def with_for_update(self, *a, **k):
            return self

    monkeypatch.setattr("app.services.cart.select", lambda *a, **k: _DummySelectable())


@pytest.mark.asyncio
async def test_add_item_invalid_quantity_raises():
    with pytest.raises(HTTPException):
        await cart_service._add_item_to_cart(
            db=cast(AsyncSession, None),
            variant_id=None,
            cart=cast(cart_service.Cart, None),
            product_id=uuid4(),
            quantity=0,
        )


@pytest.mark.asyncio
async def test_add_item_cart_not_found_raises():
    db = DummyDB()
    with pytest.raises(HTTPException):
        await cart_service._add_item_to_cart(
            db=cast(AsyncSession, db),
            variant_id=None,
            cart=cast(cart_service.Cart, None),
            product_id=uuid4(),
            quantity=1,
        )


@pytest.mark.asyncio
async def test_update_cart_item_remove():
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1)
    cart_item = SimpleNamespace(cart_id=cart_id, id=uuid4(), quantity=2)
    db = DummyDB(
        get_map={
            (cart.__class__, cart_id): cart,
        }
    )
    # monkeypatch cart class reference for get lookup
    # use actual Cart model class type key - cart_service.Cart is imported in module
    db._get_map = {(cart_service.Cart, cart_id): cart}

    res = await cart_service._update_cart_item(
        db=cast(AsyncSession, db),
        cart_item=cast(cart_service.CartItem, cart_item),
        quantity=0,
    )
    assert res is None
    assert cart.version == 2


@pytest.mark.asyncio
async def test_update_cart_item_negative_raises():
    cart_item = SimpleNamespace(cart_id=uuid4(), id=uuid4(), quantity=1)
    db = DummyDB()
    with pytest.raises(HTTPException):
        await cart_service._update_cart_item(
            db=cast(AsyncSession, db),
            cart_item=cast(cart_service.CartItem, cart_item),
            quantity=-1,
        )


@pytest.mark.asyncio
async def test_merge_guest_cart_no_guest_returns_same(monkeypatch):
    # Make execute return no guest cart
    db = DummyDB(execute_result=DummyExecuteResult(None))
    cart = SimpleNamespace(id=uuid4(), version=1, items=[])
    res = await cart_service._merge_guest_cart(
        db=cast(AsyncSession, db),
        cart=cast(cart_service.Cart, cart),
        session_id="sess",
        user_id=uuid4(),
    )
    assert res is cart


@pytest.mark.asyncio
async def test_add_item_product_not_found():
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1)
    # product select returns None
    db = DummyDBMulti(
        execute_results=[DummyExecuteResult(None)],
        get_map={(cart_service.Cart, cart_id): cart},
    )

    with pytest.raises(HTTPException) as exc:
        await cart_service._add_item_to_cart(
            db=cast(AsyncSession, db),
            variant_id=None,
            cart=cast(cart_service.Cart, cart),
            product_id=uuid4(),
            quantity=1,
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_add_item_requires_variant():
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1)
    # product has variants -> returned by select
    product = SimpleNamespace(id=uuid4(), variants=[SimpleNamespace(id=uuid4())])
    db = DummyDBMulti(
        execute_results=[DummyExecuteResult(product)],
        get_map={(cart_service.Cart, cart_id): cart},
    )

    with pytest.raises(HTTPException) as exc:
        await cart_service._add_item_to_cart(
            db=cast(AsyncSession, db),
            variant_id=None,
            cart=cast(cart_service.Cart, cart),
            product_id=product.id,
            quantity=1,
        )

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_add_item_existing_updates():
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1)

    product = SimpleNamespace(id=uuid4(), variants=[])
    # Sequence of execute results:
    # 1: product select -> product
    # 2: update CartItem returning id -> scalar_one_or_none returns some id (truthy)
    # 3: cart_version update -> returns new version
    # 4: select CartItem -> returns item
    existing_item = SimpleNamespace(
        id=uuid4(), cart_id=cart_id, product_id=product.id, quantity=5
    )
    db = DummyDBMulti(
        execute_results=[
            DummyExecuteResult(product),
            DummyExecuteResult(uuid4()),
            DummyExecuteResult(2),
            DummyExecuteResult([existing_item]),
        ],
        get_map={(cart_service.Cart, cart_id): cart},
    )

    res = await cart_service._add_item_to_cart(
        db=cast(AsyncSession, db),
        variant_id=None,
        cart=cast(cart_service.Cart, cart),
        product_id=product.id,
        quantity=3,
    )

    assert res is not None


@pytest.mark.asyncio
async def test_add_item_create_new(monkeypatch):
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1)
    product = SimpleNamespace(id=uuid4(), variants=[])

    # Sequence: product select, update (no existing item -> None), cart version update -> returns new version
    new_item = SimpleNamespace(
        id=uuid4(), cart_id=cart_id, product_id=product.id, quantity=2
    )
    db = DummyDBMulti(
        execute_results=[
            DummyExecuteResult(product),
            DummyExecuteResult(None),
            DummyExecuteResult(2),
        ],
        get_map={(cart_service.Cart, cart_id): cart},
    )

    # Monkeypatch db.refresh to set id on new_item when called from the service
    async def _refresh(obj):
        # emulate DB assigning id
        if not getattr(obj, "id", None):
            obj.id = new_item.id

    db.refresh = _refresh

    # Avoid using SQLAlchemy's update() on a mapped class in this isolated test
    class _ChainableUpdate:
        def where(self, *a, **k):
            return self

        def values(self, *a, **k):
            return self

        def returning(self, *a, **k):
            return self

    monkeypatch.setattr("app.services.cart.update", lambda *a, **k: _ChainableUpdate())
    # Make and_ produce a SQL expression that SQLAlchemy will accept for this test
    from sqlalchemy import text

    monkeypatch.setattr("app.services.cart.and_", lambda *a, **k: text("1=1"))

    # Replace the ORM CartItem with a lightweight fake so construction doesn't trigger SQLAlchemy mapper work
    class _FakeCol:
        def __init__(self, name):
            self.name = name

        def __eq__(self, other):  # type: ignore[reportIncompatibleMethodOverride]
            return f"{self.name}=={other}"

        def is_(self, other):
            return f"{self.name} IS {other}"

        def __add__(self, other):
            return f"{self.name}+{other}"

    class FakeCartItem:
        cart_id = _FakeCol("cart_id")
        variant_id = _FakeCol("variant_id")
        product_id = _FakeCol("product_id")
        quantity = _FakeCol("quantity")
        id = _FakeCol("id")

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    cart_service.CartItem = FakeCartItem

    res = await cart_service._add_item_to_cart(
        db=cast(AsyncSession, db),
        variant_id=None,
        cart=cast(cart_service.Cart, cart),
        product_id=product.id,
        quantity=2,
    )

    assert getattr(res, "product_id", None) == product.id


@pytest.mark.asyncio
async def test_update_cart_item_update_quantity():
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1)
    cart_item = SimpleNamespace(cart_id=cart_id, id=uuid4(), quantity=2)
    db = DummyDB(get_map={(cart_service.Cart, cart_id): cart})

    res = await cart_service._update_cart_item(
        db=cast(AsyncSession, db),
        cart_item=cast(cart_service.CartItem, cart_item),
        quantity=5,
    )

    assert res is not None
    assert res.quantity == 5
    assert cart.version == 2


@pytest.mark.asyncio
async def test_merge_guest_cart_merges_and_deletes(monkeypatch):
    cart_id = uuid4()
    cart = SimpleNamespace(id=cart_id, version=1, items=[])

    guest_item = SimpleNamespace(variant_id=None, product_id=uuid4(), quantity=1)
    guest_cart = SimpleNamespace(id=uuid4(), items=[guest_item])

    # execute returns guest cart on first call
    db = DummyDBMulti(execute_results=[DummyExecuteResult(guest_cart)])

    calls = []

    async def fake_add_item(
        db, variant_id, cart, product_id, quantity, commit=False, **kw
    ):
        calls.append((variant_id, product_id, quantity))

    monkeypatch.setattr("app.services.cart._add_item_to_cart", fake_add_item)

    res = await cart_service._merge_guest_cart(
        db=cast(AsyncSession, db),
        cart=cast(cart_service.Cart, cart),
        session_id="sess",
        user_id=uuid4(),
    )

    assert len(calls) == 1
    assert db.deleted and db.deleted[0] == guest_cart
    assert cart.version == 2
    assert res is cart
