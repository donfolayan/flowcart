from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logs.logging_utils import get_logger
from app.models.address import Address
from app.schemas.address import AddressCreate, AddressUpdate

logger = get_logger("app.address")


class AddressService:
    """Business logic for address management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: AddressCreate) -> Address:
        new_address = Address(**payload.model_dump())
        self.db.add(new_address)
        try:
            await self.db.commit()
        except IntegrityError as ie:
            logger.debug("IntegrityError on creating address: %s", str(ie))
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity Error - {str(ie)}",
            ) from ie
        except Exception as e:
            try:
                await self.db.rollback()
            except Exception:
                pass
            logger.exception(
                "Failed to create address",
                extra={"payload": payload.model_dump()},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal Server Error - {str(e)}",
            )
        await self.db.refresh(new_address)
        return new_address

    async def get(self, address_id: UUID) -> Address:
        address = await self.db.get(Address, address_id)
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found",
            )
        return address

    async def update(self, address_id: UUID, payload: AddressUpdate) -> Address:
        address = await self.db.get(Address, address_id)

        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found",
            )

        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(address, key, value)
        try:
            await self.db.commit()
        except IntegrityError as ie:
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Integrity Error - {str(ie)}",
            ) from ie
        except Exception as e:
            try:
                await self.db.rollback()
            except Exception:
                pass
            logger.exception(
                "Failed to update address",
                extra={"address_id": str(address_id), "payload": payload.model_dump()},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal Server Error - {str(e)}",
            )
        await self.db.refresh(address)
        return address
