from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import Optional, List
from uuid import UUID
from app.enums.promo_enum import PromoTypeEnum
from datetime import datetime, timezone


class PromoCodeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str = Field(..., max_length=50, description="The promo code string")
    promo_type: PromoTypeEnum = Field(..., description="Type of the promo code")
    value_cents: Optional[int] = Field(
        None, ge=0, description="Fixed amount discount in cents"
    )
    percent_basis_points: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="Percentage discount in basis points (1% = 100 basis points)",
    )
    max_discount_cents: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum discount amount in cents for percentage-based promo codes",
    )
    min_subtotal_cents: Optional[int] = Field(
        None, ge=0, description="Minimum cart subtotal in cents to apply the promo code"
    )
    usage_limit: Optional[int] = Field(
        None, gt=0, description="Total number of times this promo code can be used"
    )
    per_user_limit: Optional[int] = Field(
        None, gt=0, description="Number of times a single user can use this promo code"
    )
    is_active: bool = Field(
        True, description="Indicates if the promo code is currently active"
    )
    starts_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Start date and time for the promo code validity",
    )
    ends_at: Optional[datetime] = Field(
        None, description="End date and time for the promo code validity"
    )
    applies_to_product_ids: Optional[List[UUID]] = Field(
        None, description="List of product IDs this promo code applies to"
    )
    applies_to_user_ids: Optional[List[UUID]] = Field(
        None, description="List of user IDs this promo code applies to"
    )
    extra_data: Optional[dict] = Field(
        None, description="Additional metadata for the promo code"
    )

    @model_validator(mode="after")
    def validate_discount_type(self):
        """Ensure exactly one discount type is set: either fixed amount or percentage."""
        has_fixed = self.value_cents is not None and self.value_cents > 0
        has_percent = (
            self.percent_basis_points is not None and self.percent_basis_points > 0
        )

        if not (has_fixed or has_percent):
            raise ValueError("Either value_cents or percent_basis_points must be set")
        if has_fixed and has_percent:
            raise ValueError("Cannot set both value_cents and percent_basis_points")

        # If percentage-based, max_discount_cents should be set
        if has_percent and self.max_discount_cents is None:
            raise ValueError(
                "max_discount_cents is required for percentage-based promo codes"
            )

        # Ensure promo_type aligns with provided discount fields
        if self.promo_type == PromoTypeEnum.PERCENTAGE:
            if not has_percent:
                raise ValueError(
                    "promo_type 'percentage' requires percent_basis_points to be set and value_cents to be unset"
                )
            if has_fixed:
                raise ValueError("promo_type 'percentage' cannot have value_cents set")
        elif self.promo_type == PromoTypeEnum.FIXED_AMOUNT:
            if not has_fixed:
                raise ValueError(
                    "promo_type 'fixed_amount' requires value_cents to be set and percent_basis_points to be unset"
                )
            if has_percent:
                raise ValueError(
                    "promo_type 'fixed_amount' cannot have percent_basis_points set"
                )

        return self


class PromoCodeCreate(PromoCodeBase):
    pass


class PromoCodeResponse(PromoCodeBase):
    id: UUID = Field(..., description="Unique identifier for the promo code")
    usage_count: int = Field(
        ..., ge=0, description="Number of times the promo code has been used"
    )
    created_at: datetime = Field(
        ..., description="Timestamp when the promo code was created"
    )
    updated_at: datetime = Field(
        ..., description="Timestamp when the promo code was last updated"
    )
    last_used_at: Optional[datetime] = Field(
        None, description="Timestamp when the promo code was last used"
    )


class PromoCodeUpdate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    promo_type: Optional[PromoTypeEnum] = Field(
        None, description="Type of the promo code"
    )
    value_cents: Optional[int] = Field(
        None, ge=0, description="Fixed amount discount in cents"
    )
    percent_basis_points: Optional[int] = Field(
        None,
        ge=1,
        le=10000,
        description="Percentage discount in basis points (1% = 100 basis points)",
    )
    max_discount_cents: Optional[int] = Field(
        None,
        ge=0,
        description="Maximum discount amount in cents for percentage-based promo codes",
    )
    min_subtotal_cents: Optional[int] = Field(
        None, ge=0, description="Minimum cart subtotal in cents to apply the promo code"
    )
    usage_limit: Optional[int] = Field(
        None, gt=0, description="Total number of times this promo code can be used"
    )
    per_user_limit: Optional[int] = Field(
        None, gt=0, description="Number of times a single user can use this promo code"
    )
    is_active: Optional[bool] = Field(
        None, description="Indicates if the promo code is currently active"
    )
    starts_at: Optional[datetime] = Field(
        None, description="Start date and time for the promo code validity"
    )
    ends_at: Optional[datetime] = Field(
        None, description="End date and time for the promo code validity"
    )
    applies_to_product_ids: Optional[List[UUID]] = Field(
        None, description="List of product IDs this promo code applies to"
    )
    applies_to_user_ids: Optional[List[UUID]] = Field(
        None, description="List of user IDs this promo code applies to"
    )
    extra_data: Optional[dict] = Field(
        None, description="Additional metadata for the promo code"
    )
