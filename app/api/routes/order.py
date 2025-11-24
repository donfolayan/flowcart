from fastapi import APIRouter, Depends, status, HTTPException, Response
from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import sqlalchemy as sa

from app.db.session import get_session
from app.core.permissions import get_current_user_optional, require_admin
from app.api.dependencies.session import get_or_create_session_id
from app.models.order import Order
from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse
from app.services.order import OrderService
from app.enums.order_enums import OrderStatusEnum

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post(
    "/",
    response_model=OrderResponse,
    status_code=status.HTTP_201_CREATED,
    description="Create a new order from a cart. Supports both authenticated users and guest checkout via session.",
)
async def create_order_from_cart(
    payload: OrderCreate,
    response: Response,
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
) -> OrderResponse:
    """
    Create an order from a cart.

    - **Authenticated users**: Identified by JWT token (user_id)
    - **Guest users**: Identified by session cookie (session_id)
    - Requires a cart_id in the payload
    - Cart must be active and belong to the user/session
    - Creates order items from cart items
    - Marks cart as completed
    """
    order_service = OrderService(db)

    order = await order_service.create_order_from_cart(
        cart_id=payload.cart_id,
        shipping_address_id=payload.shipping_address_id,
        user_id=user_id if user_id else None,
        session_id=session_id if not user_id else None,
        billing_address_id=payload.billing_address_id,
        billing_address_same_as_shipping=payload.billing_address_same_as_shipping,
        idempotency_key=payload.idempotency_key,
    )

    return OrderResponse.model_validate(order)


@router.get(
    "/",
    response_model=List[OrderResponse],
    description="Get all orders for the current user or session",
)
async def get_user_orders(
    skip: int = 0,
    limit: int = 20,
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
) -> List[OrderResponse]:
    """
    Get all orders for the authenticated user or guest session.

    - **Authenticated users**: Returns orders by user_id
    - **Guest users**: Returns orders by session_id (not yet in service, needs update)
    """
    order_service = OrderService(db)

    if user_id:
        orders = await order_service.get_user_orders(
            user_id=user_id, skip=skip, limit=limit
        )
    else:
        # For guest users, query by session_id
        stmt = (
            select(Order)
            .where(Order.session_id == session_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        orders = result.scalars().all()

    return [OrderResponse.model_validate(order) for order in orders]


@router.get(
    "/{order_id}",
    response_model=OrderResponse,
    description="Get a specific order by ID",
)
async def get_order(
    order_id: UUID,
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
) -> OrderResponse:
    """
    Get a specific order by ID.

    - Verifies the order belongs to the user or session
    - Returns 404 if order not found
    - Returns 403 if order doesn't belong to user/session
    """
    order_service = OrderService(db)

    if user_id:
        # Use service for authenticated users
        order = await order_service.get_order_by_id(order_id=order_id, user_id=user_id)
    else:
        # For guest users, query by session_id
        stmt = select(Order).where(Order.id == order_id)
        result = await db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        # Verify order belongs to session
        if order.session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Order does not belong to your session",
            )

    return OrderResponse.model_validate(order)


@router.patch(
    "/{order_id}",
    response_model=OrderResponse,
    description="Update an order status (admin only)",
)
async def update_order(
    order_id: UUID,
    payload: OrderUpdate,
    admin_user: UUID = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> OrderResponse:
    """
    Update an order status. Admin only.

    - Supports optimistic concurrency control via version field
    - Validates status transitions via state machine
    """
    order_service = OrderService(db)

    # For now, we only support status updates
    if payload.status is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status is required for order updates",
        )

    order = await order_service.update_order_status(
        order_id=order_id,
        user_id=admin_user,  # Admin is acting on behalf of system
        new_status=payload.status,
        version=payload.version if payload.version else 1,
    )

    return OrderResponse.model_validate(order)


@router.delete(
    "/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    description="Cancel an order",
)
async def cancel_order(
    order_id: UUID,
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
) -> None:
    """
    Cancel an order (soft delete by changing status to 'cancelled').

    - Users can only cancel their own orders
    - Can only cancel orders in 'pending' or 'confirmed' status
    """
    stmt = select(Order).where(Order.id == order_id)
    result = await db.execute(stmt)
    order = result.scalar_one_or_none()

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
        )

    # Verify order belongs to user or session
    if user_id and order.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Order does not belong to you"
        )
    elif not user_id and order.session_id != session_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Order does not belong to your session",
        )

    # Check if order can be cancelled
    if order.status not in [OrderStatusEnum.PENDING, OrderStatusEnum.AWAITING_PAYMENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {order.status}",
        )

    order.status = OrderStatusEnum.CANCELLED
    order.canceled_at = sa.func.now()

    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel order: {str(e)}",
        )


# Admin-only endpoints


@router.get(
    "/admin/all",
    response_model=List[OrderResponse],
    description="Get all orders (admin only)",
)
async def get_all_orders(
    skip: int = 0,
    limit: int = 100,
    admin_user: UUID = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
) -> List[OrderResponse]:
    """
    Get all orders across all users. Admin only.

    - Supports pagination via skip/limit
    - Ordered by creation date (newest first)
    """
    stmt = select(Order).order_by(Order.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(stmt)
    orders = result.scalars().all()

    return [OrderResponse.model_validate(order) for order in orders]
