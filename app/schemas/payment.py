from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from uuid import UUID
from datetime import datetime
from app.enums.payment_status_enums import PaymentStatusEnum
from app.enums.currency_enums import CurrencyEnum


class PaymentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider: str = Field(
        ..., description="Payment provider name (e.g., Stripe, PayPal)", max_length=100
    )
    provider_id: str = Field(
        ..., description="Unique identifier from the payment provider", max_length=255
    )
    status: PaymentStatusEnum = Field(..., description="Current status of the payment")
    amount_cents: int = Field(..., description="Payment amount in cents", ge=0)
    currency: CurrencyEnum = Field(
        CurrencyEnum.USD, description="Currency of the payment"
    )


class PaymentCreate(PaymentBase):
    order_id: UUID = Field(..., description="Unique identifier of the associated order")


class PaymentUpdate(BaseModel):
    status: Optional[PaymentStatusEnum] = Field(
        None, description="Updated payment status"
    )
    provider_id: Optional[str] = Field(
        None, description="Updated provider identifier", max_length=255
    )


class PaymentResponse(PaymentBase):
    id: UUID = Field(..., description="Unique identifier of the payment")
    order_id: UUID = Field(..., description="Unique identifier of the associated order")
    created_at: datetime = Field(..., description="Creation timestamp of the payment")
    updated_at: datetime = Field(
        ..., description="Last update timestamp of the payment"
    )
