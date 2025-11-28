from __future__ import annotations
from typing import Any
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.models.order import Order
from app.enums.order_enums import OrderStatusEnum

ADDRESS_SNAPSHOT_FIELDS = (
    "name",
    "company",
    "line1",
    "line2",
    "city",
    "region",
    "postal_code",
    "country",
    "phone",
    "email",
    "extra",
)


def _address_to_snapshot(address) -> dict | None:
    if address is None:
        return None
    return {f: getattr(address, f) for f in ADDRESS_SNAPSHOT_FIELDS}


def populate_order_address_snapshots(
    session: Session, flush_context: Any, instances: Any
):
    """Before flush: ensure orders have immutable address snapshots once they are placed or status transitions.
    Rules:
    - On new Order inserts, if snapshot fields are empty but address relations exist, populate.
    - On updates where status moves to 'paid' or 'fulfilled' and snapshots still empty, populate.
    """
    for obj in session.new.union(session.dirty):
        if not isinstance(obj, Order):
            continue
        # Always populate on insert if missing
        if obj.shipping_address_snapshot is None and obj.shipping_address is not None:
            obj.shipping_address_snapshot = _address_to_snapshot(obj.shipping_address)
        if obj.billing_address_same_as_shipping:
            # Mirror shipping snapshot (make a shallow copy to avoid aliasing)
            if (
                obj.billing_address_snapshot is None
                and obj.shipping_address_snapshot is not None
            ):
                obj.billing_address_snapshot = dict(obj.shipping_address_snapshot)
        else:
            if obj.billing_address_snapshot is None and obj.billing_address is not None:
                obj.billing_address_snapshot = _address_to_snapshot(obj.billing_address)
        # Additional safeguard on status transition to paid or fulfilled
        if obj.status in {OrderStatusEnum.PAID, OrderStatusEnum.FULFILLED}:
            if (
                obj.shipping_address_snapshot is None
                and obj.shipping_address is not None
            ):
                obj.shipping_address_snapshot = _address_to_snapshot(
                    obj.shipping_address
                )
            if obj.billing_address_snapshot is None:
                if obj.billing_address_same_as_shipping:
                    # copy to ensure snapshots are independent
                    obj.billing_address_snapshot = (
                        dict(obj.shipping_address_snapshot)
                        if obj.shipping_address_snapshot is not None
                        else None
                    )
                elif obj.billing_address is not None:
                    obj.billing_address_snapshot = _address_to_snapshot(
                        obj.billing_address
                    )


def register_listeners() -> None:
    """Register all database event listeners.

    Call this once during application startup (e.g., in FastAPI lifespan)
    to attach lifecycle hooks for snapshot population and other DB events.
    """
    event.listen(Session, "before_flush", populate_order_address_snapshots)
