from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.registry import get_payment_provider
from app.core.security import get_current_user
from app.db.session import get_session
from app.core.payment.payment_error import PaymentError
from app.core.payment.status_mapping import map_stripe_status_to_payment_status

from app.models.order import Order
from app.models.payment import Payment
from app.enums.payment_status_enums import PaymentStatusEnum
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

    if getattr(order, "paid_at", None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already paid",
        )

    amount_cents = int(order.total_cents)
    currency = getattr(order.currency, "value", order.currency).lower()

    provider_name = "stripe"  # or from config.PAYMENT_PROVIDER
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
            metadata={"order_id": str(order.id)},
        )
    except PaymentError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Payment processing failed: {str(e)}",
        ) from e

    provider_id = intent.get("id") or ""
    intent_status = intent.get("status") or ""
    payment_status = map_stripe_status_to_payment_status(intent_status)

    # Upsert Payment
    stmt = select(Payment).where(Payment.order_id == order.id)
    result = await db.execute(stmt)
    payment: Payment | None = result.scalar_one_or_none()

    if payment is None:
        payment = Payment(
            order_id=order.id,
            provider=provider_name,
            provider_id=provider_id,
            status=payment_status,
            amount_cents=amount_cents,
            currency=order.currency,
        )
        db.add(payment)
    else:
        payment.provider = provider_name
        payment.provider_id = provider_id
        payment.status = payment_status
        payment.amount_cents = amount_cents
        payment.currency = order.currency

    if payment_status == PaymentStatusEnum.COMPLETED and hasattr(order, "paid_at"):
        from datetime import datetime, timezone

        order.paid_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(payment)

    return OrderPaymentResponse(
        order_id=order.id,
        payment_intent_id=payment.provider_id,
        payment_status=payment.status,
        client_secret=intent.get("client_secret"),
    )
