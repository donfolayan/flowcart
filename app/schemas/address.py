from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import Optional
from uuid import UUID
from datetime import datetime


class AddressBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Optional[str] = Field(
        None, description="Full name associated with the address"
    )
    company: Optional[str] = Field(
        None, description="Company name associated with the address"
    )
    line1: str = Field(
        ..., description="First line of the street address", max_length=255
    )
    line2: Optional[str] = Field(
        None, description="Second line of the street address", max_length=255
    )
    city: str = Field(..., description="City of the address")
    region: Optional[str] = Field(None, description="State or region of the address")
    postal_code: str = Field(..., description="Postal or ZIP code of the address")
    country: str = Field(
        ...,
        description="Country code (ISO2) of the address",
        min_length=2,
        max_length=2,
    )
    phone: Optional[str] = Field(
        None, description="Phone number associated with the address"
    )
    email: Optional[EmailStr] = Field(
        None, description="Email address associated with the address"
    )


class AddressCreate(AddressBase):
    pass


class AddressUpdate(BaseModel):
    id: UUID = Field(..., description="Unique identifier of the address")

    name: Optional[str] = Field(
        None, description="Full name associated with the address"
    )
    company: Optional[str] = Field(
        None, description="Company name associated with the address"
    )
    line1: Optional[str] = Field(
        None, description="First line of the street address", max_length=255
    )
    line2: Optional[str] = Field(
        None, description="Second line of the street address", max_length=255
    )
    city: Optional[str] = Field(None, description="City of the address")
    region: Optional[str] = Field(None, description="State or region of the address")
    postal_code: Optional[str] = Field(
        None, description="Postal or ZIP code of the address"
    )
    country: Optional[str] = Field(
        None,
        description="Country code (ISO2) of the address",
        min_length=2,
        max_length=2,
    )
    phone: Optional[str] = Field(
        None, description="Phone number associated with the address"
    )
    email: Optional[EmailStr] = Field(
        None, description="Email address associated with the address"
    )


class AddressResponse(AddressBase):
    id: UUID = Field(..., description="Unique identifier of the address")
    user_id: Optional[UUID] = Field(
        None, description="Unique identifier of the user associated with the address"
    )
    created_at: datetime = Field(..., description="Creation timestamp of the address")
