import pytest
from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from app.api.routes import address as address_routes
from app.schemas.address import AddressCreate, AddressUpdate


def make_address(**kwargs):
    """Helper to create an address-like object."""
    defaults = {
        "id": uuid4(),
        "line1": "123 Main St",
        "line2": None,
        "city": "Townsville",
        "region": None,
        "postal_code": "11111",
        "country": "US",
        "name": None,
        "company": None,
        "phone": None,
        "email": None,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_create_address_success():
    address = make_address(line1="123 A St")

    with patch.object(address_routes, "AddressService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(return_value=address)
        mock_service_class.return_value = mock_service

        payload = AddressCreate(
            name=None,
            company=None,
            line1="123 A St",
            line2=None,
            city="Townsville",
            region=None,
            postal_code="11111",
            country="US",
            phone=None,
            email=None,
        )

        res = await address_routes.create_address(payload, db=AsyncMock())
        assert res.line1 == "123 A St"


@pytest.mark.asyncio
async def test_create_address_integrity_error():
    with patch.object(address_routes, "AddressService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.create = AsyncMock(
            side_effect=HTTPException(status_code=400, detail="Integrity error")
        )
        mock_service_class.return_value = mock_service

        payload = AddressCreate(
            name=None,
            company=None,
            line1="x",
            line2=None,
            city="X",
            region=None,
            postal_code="1",
            country="US",
            phone=None,
            email=None,
        )

        with pytest.raises(HTTPException) as exc:
            await address_routes.create_address(payload, db=AsyncMock())
        assert exc.value.status_code == 400


@pytest.mark.asyncio
async def test_get_address_found():
    address = make_address(line1="Found St")

    with patch.object(address_routes, "AddressService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.get = AsyncMock(return_value=address)
        mock_service_class.return_value = mock_service

        res = await address_routes.get_address(address.id, db=AsyncMock())
        assert res.line1 == "Found St"


@pytest.mark.asyncio
async def test_get_address_not_found():
    with patch.object(address_routes, "AddressService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.get = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Address not found")
        )
        mock_service_class.return_value = mock_service

        with pytest.raises(HTTPException) as exc:
            await address_routes.get_address(uuid4(), db=AsyncMock())
        assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_update_address_success():
    address = make_address(line1="Updated St")

    with patch.object(address_routes, "AddressService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.update = AsyncMock(return_value=address)
        mock_service_class.return_value = mock_service

        payload = AddressUpdate(
            id=address.id,
            name=None,
            company=None,
            line1="Updated St",
            line2=None,
            city=None,
            region=None,
            postal_code=None,
            country=None,
            phone=None,
            email=None,
        )

        res = await address_routes.update_address(address.id, payload, db=AsyncMock())
        assert res.line1 == "Updated St"


@pytest.mark.asyncio
async def test_update_address_not_found():
    address_id = uuid4()
    with patch.object(address_routes, "AddressService") as mock_service_class:
        mock_service = AsyncMock()
        mock_service.update = AsyncMock(
            side_effect=HTTPException(status_code=404, detail="Address not found")
        )
        mock_service_class.return_value = mock_service

        payload = AddressUpdate(
            id=address_id,
            name=None,
            company=None,
            line1="x",
            line2=None,
            city=None,
            region=None,
            postal_code=None,
            country=None,
            phone=None,
            email=None,
        )

        with pytest.raises(HTTPException) as exc:
            await address_routes.update_address(address_id, payload, db=AsyncMock())
        assert exc.value.status_code == 404
