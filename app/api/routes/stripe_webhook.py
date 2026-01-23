from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.logs.logging_utils import get_logger
from app.core.payment.stripe_provider import StripeProvider
from app.core.payment.payment_error import PaymentError
from app.db.session import get_session
from app.models.payment import Payment
from app.models.order import Order
from app.enums.payment_status_enums import PaymentStatusEnum

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])

provider = StripeProvider()
logger = get_logger("app.webhooks")


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
        logger.error(
            "Stripe webhook signature verification failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
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
        logger.info(
            "Stripe webhook received but no object to process",
            extra={"event_type": event_type},
        )
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

    logger.info(
        "Processing Stripe webhook",
        extra={
            "event_type": event_type,
            "payment_intent_id": payment_intent_id,
            "order_id": str(order_uuid) if order_uuid else None,
        },
    )

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
        logger.warning(
            "No payment record found for Stripe webhook",
            extra={
                "payment_intent_id": payment_intent_id,
                "order_id": str(order_uuid) if order_uuid else None,
            },
        )
        return {"received": True}

    try:
        if event_type == "payment_intent.succeeded":
            payment.status = PaymentStatusEnum.COMPLETED
            logger.info(
                "Payment completed successfully",
                extra={
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order_id) if payment.order_id else None,
                    "amount": str(payment.amount)
                    if hasattr(payment, "amount")
                    else None,
                },
            )

            # Optionally reflect onto Order
            if payment.order_id:
                order_result = await db.execute(
                    select(Order).where(Order.id == payment.order_id)
                )
                order: Optional[Order] = order_result.scalar_one_or_none()
                if order and hasattr(order, "paid_at"):
                    order.paid_at = datetime.now(timezone.utc)

        elif event_type == "payment_intent.payment_failed":
            payment.status = PaymentStatusEnum.FAILED
            logger.warning(
                "Payment failed",
                extra={
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order_id) if payment.order_id else None,
                },
            )

        elif event_type == "payment_intent.canceled":
            payment.status = PaymentStatusEnum.CANCELLED
            logger.info(
                "Payment cancelled",
                extra={
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order_id) if payment.order_id else None,
                },
            )

        elif event_type == "charge.refunded":
            payment.status = PaymentStatusEnum.REFUNDED
            logger.info(
                "Payment refunded",
                extra={
                    "payment_id": str(payment.id),
                    "order_id": str(payment.order_id) if payment.order_id else None,
                },
            )

        elif event_type == "payment_intent.amount_capturable_updated":
            amount_capturable = stripe_object.get("amount_capturable")
            if amount_capturable is not None:
                payment.amount_capturable = amount_capturable
                logger.info(
                    "Payment amount capturable updated",
                    extra={
                        "payment_id": str(payment.id),
                        "order_id": str(payment.order_id) if payment.order_id else None,
                        "amount_capturable": str(amount_capturable),
                    },
                )

        await db.commit()
    except Exception:
        # Log the error but still return 200 so Stripe stops retrying
        logger.exception(
            "Error processing Stripe webhook",
            extra={
                "event_type": event_type,
                "payment_intent_id": payment_intent_id,
            },
        )
        return {"received": True}

    return {"received": True}
