from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.payment.stripe_provider import StripeProvider
from app.core.payment.payment_error import PaymentError
from app.db.session import get_session
from app.models.payment import Payment
from app.models.order import Order
from app.enums.payment_status_enums import PaymentStatusEnum

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

provider = StripeProvider()


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    payload = await request.body()
    sig_header: Optional[str] = request.headers.get("Stripe-Signature")

    if sig_header is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header",
        )

    try:
        event = await provider.handle_webhook(payload, sig_header)
    except PaymentError as e:
        print("Stripe webhook error during verification:", repr(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    event_type = event.get("type")
    stripe_object = event.get("object")
    if not isinstance(stripe_object, dict):
        # Backwards compatibility: the sanitized payload may still expose data.object
        stripe_object = (event.get("data") or {}).get("object")

    if not isinstance(stripe_object, dict):
        # Nothing to link to in DB, just ack
        return {"received": True}

    payment_intent_id = stripe_object.get("id")
    metadata = stripe_object.get("metadata") or {}
    order_uuid: Optional[UUID] = None
    order_id_raw: Optional[str] = metadata.get("order_id")
    if order_id_raw:
        try:
            order_uuid = UUID(order_id_raw)
        except (ValueError, TypeError):
            order_uuid = None

    print("Stripe webhook event:", event_type, "payment_intent_id:", payment_intent_id)

    if not payment_intent_id:
        return {"received": True}

    # Look up Payment row by provider + provider_id
    stmt = select(Payment).where(
        Payment.provider == "stripe",
        Payment.provider_id == payment_intent_id,
    )
    result = await db.execute(stmt)
    payment: Optional[Payment] = result.scalar_one_or_none()

    if not payment and order_uuid:
        # Fallback lookup by order in case the provider id wasn't persisted yet
        order_stmt = select(Payment).where(Payment.order_id == order_uuid)
        order_result = await db.execute(order_stmt)
        payment = order_result.scalar_one_or_none()
        if payment:
            payment.provider = "stripe"
            payment.provider_id = payment_intent_id
            if not payment.order_id:
                payment.order_id = order_uuid

    if not payment:
        print("No Payment found for provider_id:", payment_intent_id)
        return {"received": True}

    try:
        if event_type == "payment_intent.succeeded":
            payment.status = PaymentStatusEnum.COMPLETED

            # Optionally reflect onto Order
            if payment.order_id:
                order_result = await db.execute(
                    select(Order).where(Order.id == payment.order_id)
                )
                order: Optional[Order] = order_result.scalar_one_or_none()
                if order and hasattr(order, "paid_at"):
                    from datetime import datetime, timezone

                    order.paid_at = datetime.now(timezone.utc)

        elif event_type == "payment_intent.payment_failed":
            payment.status = PaymentStatusEnum.FAILED

        # You can add handling for refund events here later

        await db.commit()
    except Exception as e:
        # Log the error but still return 200 so Stripe stops retrying
        print("ERROR handling Stripe webhook:", repr(e))
        return {"received": True}

    return {"received": True}
