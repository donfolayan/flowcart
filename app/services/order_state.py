from typing import Dict, List
from app.enums.order_enums import OrderStatusEnum

# Simple state transitions mapping; centralizes allowed transitions for orders.
allowed_transitions: Dict[OrderStatusEnum, List[OrderStatusEnum]] = {
    OrderStatusEnum.PENDING: [
        OrderStatusEnum.AWAITING_PAYMENT,
        OrderStatusEnum.PAID,
        OrderStatusEnum.CANCELLED,
    ],
    OrderStatusEnum.AWAITING_PAYMENT: [OrderStatusEnum.PAID, OrderStatusEnum.CANCELLED],
    OrderStatusEnum.PAID: [OrderStatusEnum.FULFILLED, OrderStatusEnum.REFUNDED],
    OrderStatusEnum.FULFILLED: [],
    OrderStatusEnum.CANCELLED: [],
    OrderStatusEnum.REFUNDED: [],
}


def can_transition(from_status: OrderStatusEnum, to_status: OrderStatusEnum) -> bool:
    """Return True if transition is allowed."""
    return to_status in allowed_transitions.get(from_status, [])


def validate_transition_or_raise(
    from_status: OrderStatusEnum, to_status: OrderStatusEnum
) -> None:
    """Raise ValueError if transition is invalid."""
    if not can_transition(from_status, to_status):
        raise ValueError(f"Invalid state transition from {from_status} to {to_status}")
