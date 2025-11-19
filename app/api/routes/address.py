from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from uuid import UUID

from app.db.session import get_session
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse

router = APIRouter(prefix="/address", tags=["Address"])


@router.post("/", response_model=AddressResponse)
async def create_address(
    payload: AddressCreate, db: AsyncSession = Depends(get_session)
) -> AddressResponse:
    """Create a new address."""
    new_address = Address(**payload.model_dump())
    db.add(new_address)
    try:
        await db.commit()
    except IntegrityError as ie:
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity Error - {str(ie)}",
        ) from ie
    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        )
    await db.refresh(new_address)
    return AddressResponse.model_validate(new_address)


@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: UUID, db: AsyncSession = Depends(get_session)
) -> AddressResponse:
    """Retrieve an address by ID."""
    address = await db.get(Address, address_id)
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )
    return AddressResponse.model_validate(address)


@router.patch("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: UUID, payload: AddressUpdate, db: AsyncSession = Depends(get_session)
) -> AddressResponse:
    """Update an exisiting address."""
    address = await db.get(Address, address_id)

    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found",
        )

    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(address, key, value)
    try:
        await db.commit()
    except IntegrityError as ie:
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Integrity Error - {str(ie)}",
        ) from ie
    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        )
    await db.refresh(address)
    return AddressResponse.model_validate(address)
