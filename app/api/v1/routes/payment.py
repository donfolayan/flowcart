from typing import Any

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.security import get_current_user
from app.db.session import get_session
from app.schemas.order_payment import OrderPaymentRequest, OrderPaymentResponse
from app.services.payment import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/orders/{order_id}/pay",
    response_model=OrderPaymentResponse,
    status_code=status.HTTP_200_OK,
)
async def pay_for_order(
    order_id: str,
    payload: OrderPaymentRequest,
    db: AsyncSession = Depends(get_session),
    current_user: Any = Depends(get_current_user),
):
    service = PaymentService(db)
    return await service.pay_for_order(
        order_id=order_id, payload=payload, current_user=current_user
    )
