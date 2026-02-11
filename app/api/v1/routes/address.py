from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.db.session import get_session
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse
from app.services.address import AddressService

router = APIRouter(prefix="/address", tags=["Address"])


@router.post("/", response_model=AddressResponse)
async def create_address(
    payload: AddressCreate, db: AsyncSession = Depends(get_session)
) -> AddressResponse:
    """Create a new address."""
    service = AddressService(db)
    new_address = await service.create(payload=payload)
    return AddressResponse.model_validate(new_address)


@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: UUID, db: AsyncSession = Depends(get_session)
) -> AddressResponse:
    """Retrieve an address by ID."""
    service = AddressService(db)
    address = await service.get(address_id=address_id)
    return AddressResponse.model_validate(address)


@router.patch("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: UUID, payload: AddressUpdate, db: AsyncSession = Depends(get_session)
) -> AddressResponse:
    """Update an exisiting address."""
    service = AddressService(db)
    address = await service.update(address_id=address_id, payload=payload)
    return AddressResponse.model_validate(address)
