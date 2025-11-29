from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.registry import get_payment_provider
from app.core.security import get_current_user
from app.db.session import get_session
from app.core.payment.payment_error import PaymentError

from app.models.order import Order
from app.schemas.order_payment import OrderPaymentRequest, OrderPaymentResponse

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
    order = await db.get(Order, order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to pay for this order",
        )
    if order.is_paid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already paid",
        )

    # Determine amount/currency from order
    amount_cents = int(order.total_amount_cents)
    currency = order.currency or "usd"

    # Get payment provider (config.PAYMENT_PROVIDER, default "stripe")
    provider_name = order.payment_provider or "stripe"
    provider = get_payment_provider(name=provider_name)
    if provider is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Payment provider '{provider_name}' is not configured",
        )

    try:
        intent = await provider.charge(
            amount_cents=amount_cents,
            currency=currency,
            payment_method_data=payload.payment_method_data,
            description=f"Order {order.id}",
            idempotency_key=payload.idempotency_key,
            capture=True,
        )
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment processing failed: {str(e)}",
        ) from e
    # 4) Persist payment info on order
    order.payment_intent_id = intent.get("id")
    order.payment_status = intent.get("status")
    order.payment_provider = provider_name
    await db.commit()
    await db.refresh(order)

    return OrderPaymentResponse(
        order_id=order.id,
        payment_intent_id=order.payment_intent_id,
        payment_status=order.payment_status,
        client_secret=intent.get("client_secret"),
    )
