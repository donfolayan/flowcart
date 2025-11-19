from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from typing import Optional, List

from app.core.config import config

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.enums.order_enums import OrderStatusEnum
from app.enums.cart_enums import CartStatus

TAX_RATE = config.TAX_RATE


class OrderService:
    """Business logic for managing orders."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_order_from_cart(
        self,
        cart_id: UUID,
        shipping_address_id: UUID,
        user_id: UUID | None = None,
        session_id: str | None = None,
        billing_address_id: Optional[UUID] = None,
        billing_address_same_as_shipping: bool = True,
        idempotency_key: Optional[str] = None,
    ) -> Order:
        """Create order from cart."""

        # Check for existing order with same idempotency key
        if idempotency_key:
            stmt = (
                select(Order)
                .options(selectinload(Order.items))
                .where(
                    Order.user_id == user_id, Order.idempotency_key == idempotency_key
                )
            )
            result = await self.db.execute(stmt)
            existing_order = result.scalar_one_or_none()

            if existing_order:
                return existing_order

        # Fetch cart and its items
        stmt = (
            select(Cart)
            .options(selectinload(Cart.items).selectinload(CartItem.product))
            .where(Cart.id == cart_id)
        )
        result = await self.db.execute(stmt)
        cart = result.scalar_one_or_none()

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
            )

        # Verify cart belongs to user or session
        if user_id and cart.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cart does not belong to the user",
            )
        if session_id and cart.session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cart does not belong to the session",
            )

        # Ensure cart is in 'active' status
        if cart.status != CartStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot create order from cart with status {cart.status.value}",
            )

        # Ensure cart has items
        if not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
            )

        # Calculate totals
        subtotal_cents = 0
        order_items_data = []

        for cart_item in cart.items:
            if not cart_item.product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product for cart item {cart_item.id} no longer available",
                )

            # Calculate line total
            line_total_cents = cart_item.quantity * cart_item.product.price_cents
            subtotal_cents += line_total_cents

            # Prepare order item data
            order_items_data.append(
                {
                    "product_id": cart_item.product.id,
                    "variant_id": cart_item.variant_id,
                    "product_name": cart_item.product.name,
                    "sku": cart_item.product.sku,
                    "product_image_url": cart_item.product.images[0]
                    if cart_item.product.images
                    else None,
                    "quantity": cart_item.quantity,
                    "unit_price_cents": cart_item.product.price_cents,
                    "total_price_cents": line_total_cents,
                }
            )

        # Calculate tax
        tax_cents = int(subtotal_cents * TAX_RATE)

        # Calculate total
        total_cents = subtotal_cents + tax_cents

        # Create order
        new_order = Order(
            cart_id=cart.id,
            user_id=user_id,
            currency=cart.currency,
            subtotal_cents=subtotal_cents,
            tax_cents=tax_cents,
            discount=0,  # TODO: Apply discount code logic
            total_cents=total_cents,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id
            if not billing_address_same_as_shipping
            else shipping_address_id,
            billing_address_same_as_shipping=billing_address_same_as_shipping,
            status=OrderStatusEnum.PENDING,
            placed_at=datetime.now(timezone.utc),
            idempotency_key=idempotency_key,
        )

        self.db.add(new_order)
        await self.db.flush()

        # Create order items
        for item_data in order_items_data:
            order_item = OrderItem(order_id=new_order.id, **item_data)
            self.db.add(order_item)

        # Mark cart as completed
        cart.status = CartStatus.COMPLETED
        cart.completed_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(new_order)
        return Order.model_validate(new_order)

    async def get_user_orders(
        self,
        user_id: UUID,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Order]:
        """Retrieve orders for a specific user with pagination."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        orders = result.scalars().all()
        return list(orders)

    async def get_order_by_id(
        self,
        order_id: UUID,
        user_id: UUID,
    ) -> Order:
        """Retrieve a specific order by ID for a user."""
        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.id == order_id, Order.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if not order.user_id == user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Order does not belong to the user",
            )

        return order

    async def update_order_status(
        self,
        order_id: UUID,
        user_id: UUID,
        new_status: OrderStatusEnum,
        version: int,
    ) -> Order:
        """Update the status of an order."""
        stmt = select(Order).where(Order.id == order_id)
        result = await self.db.execute(stmt)
        order = result.scalar_one_or_none()

        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Order not found"
            )

        if order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Order does not belong to the user",
            )

        if order.version != version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order has been modified by another process. Please refresh and try again.",
            )

        # Validadte status transition
        # TODO: Add proper state machine validation

        valid_transitions = {
            OrderStatusEnum.PENDING: [OrderStatusEnum.PAID, OrderStatusEnum.CANCELLED],
            OrderStatusEnum.AWAITING_PAYMENT: [
                OrderStatusEnum.PAID,
                OrderStatusEnum.CANCELLED,
            ],
            OrderStatusEnum.PAID: [OrderStatusEnum.FULFILLED, OrderStatusEnum.REFUNDED],
            OrderStatusEnum.FULFILLED: [],
            OrderStatusEnum.CANCELLED: [],
            OrderStatusEnum.REFUNDED: [],
        }

        if new_status not in valid_transitions.get(order.status, []):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from {order.status.value} to {new_status.value}",
            )

        order.status = new_status
        order.version += 1

        if new_status == OrderStatusEnum.PAID:
            order.paid_at = datetime.now(timezone.utc)
        elif new_status == OrderStatusEnum.FULFILLED:
            order.fulfilled_at = datetime.now(timezone.utc)
        elif new_status == OrderStatusEnum.CANCELLED:
            order.canceled_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(order)
        return order
