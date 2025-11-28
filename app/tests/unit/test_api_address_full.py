import pytest
from typing import cast, Any
from types import SimpleNamespace
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException
from uuid import uuid4

from app.schemas.address import AddressCreate


class StubAddress:
    id: Any = None
    line1: Any = None
    city: Any = None
    postal_code: Any = None
    country: Any = None
    created_at: Any = None
    updated_at: Any = None

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)
        # ensure an id exists for responses
        if not getattr(self, "id", None):
            try:
                from uuid import uuid4

                self.id = uuid4()
            except Exception:
                self.id = 1
        # fill timestamps and minimal required fields if missing
        from datetime import datetime

        if not getattr(self, "created_at", None):
            self.created_at = datetime.utcnow()
        if not getattr(self, "updated_at", None):
            self.updated_at = datetime.utcnow()
        if not getattr(self, "postal_code", None):
            self.postal_code = getattr(self, "postal_code", "00000")
        if not getattr(self, "country", None):
            self.country = getattr(self, "country", "US")
        if not getattr(self, "city", None):
            self.city = getattr(self, "city", "City")


class FakeDB:
    def __init__(self, get_result=None, commit_raises=None):
        self.get_result = get_result
        self.commit_raises = commit_raises
        self.added = None
        self.committed = False

    def add(self, obj):
        self.added = obj

    async def commit(self):
        if self.commit_raises:
            raise self.commit_raises
        self.committed = True

    async def refresh(self, obj):
        # mimic ORM refresh: do nothing
        return None

    async def rollback(self):
        return None

    async def get(self, model, id_):
        return self.get_result


@pytest.mark.asyncio
async def test_create_address_success(monkeypatch):
    from app.api.routes import address as address_routes

    payload = AddressCreate(
        line1="123 A St",
        city="Townsville",
        postal_code="11111",
        country="US",
        name=None,
        company=None,
        line2=None,
        region=None,
        phone=None,
        email=None,
    )

    fake_db = FakeDB()

    monkeypatch.setattr(address_routes, "Address", StubAddress)

    res = await address_routes.create_address(payload, cast(AsyncSession, fake_db))

    # response should include the line1 we provided
    assert getattr(res, "line1", None) == "123 A St" or (
        isinstance(res, dict) and res.get("line1") == "123 A St"
    )


@pytest.mark.asyncio
async def test_create_address_integrity_error(monkeypatch):
    from app.api.routes import address as address_routes

    payload = AddressCreate(
        line1="x",
        city="X",
        postal_code="1",
        country="US",
        name=None,
        company=None,
        line2=None,
        region=None,
        phone=None,
        email=None,
    )
    fake_db = FakeDB(commit_raises=IntegrityError("dup", {}, Exception("orig")))

    monkeypatch.setattr(address_routes, "Address", StubAddress)

    with pytest.raises(HTTPException) as exc:
        await address_routes.create_address(payload, cast(AsyncSession, fake_db))

    assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_address_found(monkeypatch):
    from app.api.routes import address as address_routes

    existing = StubAddress(
        id=uuid4(), line1="Found St", city="Nowhere", postal_code="11111", country="US"
    )
    fake_db = FakeDB(get_result=existing)

    res = await address_routes.get_address(existing.id, cast(AsyncSession, fake_db))

    assert getattr(res, "line1", None) == "Found St" or (
        isinstance(res, dict) and res.get("line1") == "Found St"
    )


@pytest.mark.asyncio
async def test_get_address_not_found():
    from app.api.routes import address as address_routes

    fake_db = FakeDB(get_result=None)

    with pytest.raises(HTTPException) as exc:
        await address_routes.get_address(uuid4(), cast(AsyncSession, fake_db))

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_address_success(monkeypatch):
    from app.api.routes import address as address_routes

    existing = StubAddress(
        id=uuid4(), line1="Old St", city="OldCity", postal_code="11111", country="US"
    )
    fake_db = FakeDB(get_result=existing)

    payload = SimpleNamespace(model_dump=lambda **kwargs: {"line1": "New St"})

    res = await address_routes.update_address(
        existing.id, cast(Any, payload), cast(AsyncSession, fake_db)
    )

    # underlying object should have been updated
    assert existing.line1 == "New St"
    assert getattr(res, "line1", None) == "New St"


@pytest.mark.asyncio
async def test_update_address_not_found():
    from app.api.routes import address as address_routes

    fake_db = FakeDB(get_result=None)
    payload = SimpleNamespace(model_dump=lambda **kwargs: {"line1": "New St"})

    with pytest.raises(HTTPException) as exc:
        await address_routes.update_address(
            uuid4(), cast(Any, payload), cast(AsyncSession, fake_db)
        )

    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_address_integrity_error(monkeypatch):
    from app.api.routes import address as address_routes

    existing = StubAddress(
        id=uuid4(), line1="Old St", city="OldCity", postal_code="11111", country="US"
    )
    fake_db = FakeDB(
        get_result=existing, commit_raises=IntegrityError("dup", {}, Exception("orig"))
    )

    payload = SimpleNamespace(model_dump=lambda **kwargs: {"line1": "New St"})

    with pytest.raises(HTTPException) as exc:
        await address_routes.update_address(
            existing.id, cast(Any, payload), cast(AsyncSession, fake_db)
        )

    assert exc.value.status_code == 400


def test_import_address_routes():
    import app.api.routes.address as addr

    assert hasattr(addr, "router")
