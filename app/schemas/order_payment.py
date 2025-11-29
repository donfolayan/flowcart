from uuid import UUID
from typing import Any, Dict, Optional
from pydantic import BaseModel


class OrderPaymentRequest(BaseModel):
    payment_method_data: Dict[str, Any]
    idempotency_key: Optional[str] = None


class OrderPaymentResponse(BaseModel):
    order_id: UUID
    payment_intent_id: Optional[str]
    payment_status: Optional[str]
    client_secret: Optional[str]
