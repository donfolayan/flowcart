import re
import datetime
from typing import Optional
from uuid import UUID
from pydantic import (
    BaseModel,
    Field,
    EmailStr,
    field_validator,
    model_validator,
    ConfigDict,
)


class UserBase(BaseModel):
    email: EmailStr = Field(..., description="Email address of the user")
    username: str = Field(..., max_length=50, description="Username of the user")


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, description="Password for the user")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[!@#$%^&*()_\-+=\[\]{};:'\",.<>/?\\|`~]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserProfile(BaseModel):
    first_name: Optional[str] = Field(
        None, max_length=100, description="First name of the user"
    )
    last_name: Optional[str] = Field(
        None, max_length=100, description="Last name of the user"
    )
    phone_number: Optional[str] = Field(
        None, max_length=20, description="Phone number of the user"
    )
    date_of_birth: Optional[datetime.date] = Field(
        None, description="Date of birth of the user"
    )


class UserUpdate(BaseModel):
    first_name: Optional[str] = Field(
        None, max_length=100, description="First name of the user"
    )
    last_name: Optional[str] = Field(
        None, max_length=100, description="Last name of the user"
    )
    phone_number: Optional[str] = Field(
        None, max_length=20, description="Phone number of the user"
    )
    date_of_birth: Optional[datetime.datetime] = Field(
        None, description="Date of birth of the user"
    )
    email: Optional[EmailStr] = Field(None, description="Email address of the user")
    username: Optional[str] = Field(
        None, max_length=50, description="Username of the user"
    )
    password: Optional[str] = Field(
        None, min_length=8, description="Password for the user"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[!@#$%^&*()_\-+=\[\]{};:'\",.<>/?\\|`~]", v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    email: Optional[EmailStr] = Field(None, description="Email address of the user")
    username: Optional[str] = Field(None, description="Username of the user")
    password: str = Field(..., description="Password for the user")

    @model_validator(mode="after")
    def validate_username_or_email(self):
        if not self.email and not self.username:
            raise ValueError("Either email or username must be provided")
        return self


class UserResponse(UserBase, UserProfile):
    id: UUID = Field(..., description="Unique identifier of the user")
    is_active: bool = Field(True, description="Indicates if the user is active")
    is_verified: bool = Field(False, description="Indicates if the user is verified")
    created_at: datetime.datetime = Field(
        ..., description="Timestamp when the user was created"
    )
    model_config = ConfigDict(from_attributes=True)
