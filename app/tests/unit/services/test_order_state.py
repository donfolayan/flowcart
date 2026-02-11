import pytest
from app.services.order_state import can_transition, validate_transition_or_raise
from app.enums.order_enums import OrderStatusEnum


def test_can_transition_allowed():
    assert can_transition(OrderStatusEnum.PENDING, OrderStatusEnum.AWAITING_PAYMENT)


def test_can_transition_disallowed():
    assert not can_transition(OrderStatusEnum.FULFILLED, OrderStatusEnum.PENDING)


def test_validate_transition_or_raise_ok():
    validate_transition_or_raise(
        OrderStatusEnum.PENDING, OrderStatusEnum.AWAITING_PAYMENT
    )


def test_validate_transition_or_raise_raises():
    with pytest.raises(ValueError):
        validate_transition_or_raise(OrderStatusEnum.FULFILLED, OrderStatusEnum.PENDING)
