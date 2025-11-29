from app.enums.payment_status_enums import PaymentStatusEnum


def map_stripe_status_to_payment_status(intent_status: str) -> PaymentStatusEnum:
    status = (intent_status or "").lower()

    # PaymentIntent statuses
    if status in {
        "requires_payment_method",
        "requires_confirmation",
        "requires_action",
    }:
        return PaymentStatusEnum.PENDING
    if status in {"processing"}:
        return PaymentStatusEnum.PROCESSING
    if status in {"requires_capture"}:
        return PaymentStatusEnum.AUTHORIZED
    if status in {"succeeded"}:
        return PaymentStatusEnum.COMPLETED
    if status in {"canceled"}:
        return PaymentStatusEnum.CANCELLED

    # Fallback
    return PaymentStatusEnum.FAILED
