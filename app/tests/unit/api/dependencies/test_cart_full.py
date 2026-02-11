import pytest
from uuid import uuid4
from types import SimpleNamespace
from sqlalchemy.exc import IntegrityError

from app.api.dependencies import cart as cart_dep


class DummyRes:
    def __init__(self, vals):
        self._vals = vals

    def scalars(self):
        class S:
            def __init__(self, v):
                self._v = v

            def first(self):
                return self._v

            def one_or_none(self):
                return self._v

        return S(self._vals)


class FakeDB:
    def __init__(self, execute_results=None, commit_raises=False):
        self._results = list(execute_results or [])
        self.added = []
        self.commit_raises = commit_raises
        self.rolled_back = False

    async def execute(self, q):
        if self._results:
            return self._results.pop(0)
        return DummyRes(None)

    def add(self, obj):
        self.added.append(obj)

    async def commit(self):
        if self.commit_raises:
            raise IntegrityError("", {}, None)  # type: ignore

    async def refresh(self, obj):
        return None

    async def rollback(self):
        self.rolled_back = True


@pytest.mark.asyncio
async def test_get_cart_or_404_raises_when_missing(monkeypatch):
    # avoid SQLAlchemy loader inspection during tests and stub select object
    monkeypatch.setattr(cart_dep, "selectinload", lambda *a, **k: None)

    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr(cart_dep, "select", DummySelect)
    fake_db = FakeDB(execute_results=[DummyRes(None)])

    with pytest.raises(Exception) as exc:
        await cart_dep.get_cart_or_404(uuid4(), db=fake_db)  # type: ignore

    assert getattr(exc.value, "status_code", None) == 404


@pytest.mark.asyncio
async def test_get_cart_or_404_returns_cart(monkeypatch):
    monkeypatch.setattr(cart_dep, "selectinload", lambda *a, **k: None)

    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr(cart_dep, "select", DummySelect)
    user_id = uuid4()
    fake_cart = SimpleNamespace(id=uuid4(), user_id=user_id, session_id=None)
    fake_db = FakeDB(execute_results=[DummyRes(fake_cart)])

    res = await cart_dep.get_cart_or_404(fake_cart.id, db=fake_db, user_id=user_id)  # type: ignore
    assert res is fake_cart


@pytest.mark.asyncio
async def test_get_or_create_cart_returns_existing(monkeypatch):
    monkeypatch.setattr(cart_dep, "selectinload", lambda *a, **k: None)

    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr(cart_dep, "select", DummySelect)
    fake_cart = SimpleNamespace(
        id=uuid4(), user_id=uuid4(), session_id=None, status="active"
    )
    fake_db = FakeDB(execute_results=[DummyRes(fake_cart)])

    res = await cart_dep.get_or_create_cart(
        db=fake_db,  # type: ignore
        user_id=fake_cart.user_id,
        session_id="s1",  # type: ignore
    )
    assert res is fake_cart


@pytest.mark.asyncio
async def test_get_or_create_cart_creates_when_missing(monkeypatch):
    monkeypatch.setattr(cart_dep, "selectinload", lambda *a, **k: None)

    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr(cart_dep, "select", DummySelect)

    # Stub Cart model so instantiation doesn't trigger mapper configuration
    class StubCart:
        # provide class attributes used in where() expressions to avoid AttributeError
        session_id = None
        status = None
        user_id = None
        id = None

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    monkeypatch.setattr(cart_dep, "Cart", StubCart)

    fake_db = FakeDB(execute_results=[DummyRes(None)])

    # call the function under test so a Cart-like object is added
    res = await cart_dep.get_or_create_cart(
        db=fake_db,  # type: ignore
        user_id=None,
        session_id="s2",  # type: ignore
    )

    # ensure a Cart-like object was added
    assert len(fake_db.added) == 1
    added = fake_db.added[0]
    assert getattr(added, "session_id", None) == "s2"
    # returned object for create may be the added object or refreshed; at least ensure session_id matches
    assert getattr(res, "session_id", "s2") == "s2"


@pytest.mark.asyncio
async def test_get_or_create_cart_sets_status_active_when_created(monkeypatch):
    # ensure created cart has status "active"
    monkeypatch.setattr(cart_dep, "selectinload", lambda *a, **k: None)

    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr(cart_dep, "select", DummySelect)

    class StubCart:
        session_id = None
        status = None
        user_id = None
        id = None

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    monkeypatch.setattr(cart_dep, "Cart", StubCart)
    fake_db = FakeDB(execute_results=[DummyRes(None)])

    await cart_dep.get_or_create_cart(db=fake_db, user_id=uuid4(), session_id=None)  # type: ignore

    assert len(fake_db.added) == 1
    added = fake_db.added[0]
    # status should be set to active for newly created carts
    assert getattr(added, "status", None) == "active"


@pytest.mark.asyncio
async def test_get_or_create_cart_handles_integrity_error_and_returns_existing(
    monkeypatch,
):
    monkeypatch.setattr(cart_dep, "selectinload", lambda *a, **k: None)

    class DummySelect:
        def __init__(self, *a, **k):
            pass

        def options(self, *a, **k):
            return self

        def where(self, *a, **k):
            return self

    monkeypatch.setattr(cart_dep, "select", DummySelect)

    # Stub Cart class to avoid mapper init
    class StubCart:
        session_id = None
        status = None
        user_id = None
        id = None

        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)

    monkeypatch.setattr(cart_dep, "Cart", StubCart)

    existing = SimpleNamespace(
        id=uuid4(), user_id=None, session_id="s3", status="active"
    )
    # first execute returns None (no cart), commit raises IntegrityError, then execute returns existing
    fake_db = FakeDB(
        execute_results=[DummyRes(None), DummyRes(existing)], commit_raises=True
    )

    res = await cart_dep.get_or_create_cart(db=fake_db, user_id=None, session_id="s3")  # type: ignore
    assert res is existing
