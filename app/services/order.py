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
from app.models.address import Address
from app.enums.order_enums import OrderStatusEnum
from app.services.promo import PromoService
from app.enums.cart_enums import CartStatus
from app.services.order_state import validate_transition_or_raise

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
        promo_code: Optional[str] = None,
    ) -> Order:
        """Create order from cart."""

        # Check for existing order with same idempotency key (user or session)
        if idempotency_key:
            if user_id:
                stmt = (
                    select(Order)
                    .options(selectinload(Order.items))
                    .where(
                        Order.user_id == user_id,
                        Order.idempotency_key == idempotency_key,
                    )
                )
            else:
                stmt = (
                    select(Order)
                    .options(selectinload(Order.items))
                    .where(
                        Order.session_id == session_id,
                        Order.idempotency_key == idempotency_key,
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

        # Apply promo code (if provided) and compute discount via PromoService
        discount_cents = 0
        applied_snapshot = None
        promo_obj = None
        if promo_code:
            promo_service = PromoService(self.db)
            promo_result = await promo_service.validate_and_compute(
                promo_code, subtotal_cents, user_id
            )
            promo_obj = promo_result.get("promo")
            discount_cents = promo_result.get("discount_cents", 0)
            applied_snapshot = promo_result.get("snapshot")

        # Calculate tax (after discount) and total
        taxable = subtotal_cents - discount_cents
        tax_cents = int(taxable * TAX_RATE)
        total_cents = subtotal_cents - discount_cents + tax_cents

        # Fetch and serialize addresses for immutable snapshots
        shipping_address: Optional[Address] = await self.db.get(
            Address, shipping_address_id
        )
        if not shipping_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Shipping address not found",
            )

        if billing_address_same_as_shipping:
            billing_address = shipping_address
        else:
            if not billing_address_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="billing_address_id required when billing_address_same_as_shipping is False",
                )
            billing_address = await self.db.get(Address, billing_address_id)
            if not billing_address:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Billing address not found",
                )

        def _serialize_address(addr: Address) -> dict:
            return {
                "id": str(addr.id),
                "name": addr.name,
                "company": addr.company,
                "line1": addr.line1,
                "line2": addr.line2,
                "city": addr.city,
                "region": addr.region,
                "postal_code": addr.postal_code,
                "country": addr.country,
                "phone": addr.phone,
                "email": addr.email,
                "extra": addr.extra or {},
            }

        shipping_snapshot = _serialize_address(shipping_address)
        billing_snapshot = _serialize_address(billing_address)

        # Create order
        new_order = Order(
            cart_id=cart.id,
            user_id=user_id,
            currency=cart.currency,
            subtotal_cents=subtotal_cents,
            tax_cents=tax_cents,
            discount_cents=discount_cents,
            total_cents=total_cents,
            promo_code=promo_code.strip().lower() if promo_code else None,
            applied_discounts_snapshot=applied_snapshot,
            shipping_address_id=shipping_address_id,
            billing_address_id=billing_address_id
            if not billing_address_same_as_shipping
            else shipping_address_id,
            billing_address_same_as_shipping=billing_address_same_as_shipping,
            shipping_address_snapshot=shipping_snapshot,
            billing_address_snapshot=billing_snapshot,
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

        # Atomically increment promo usage (if promo applied)
        if promo_obj is not None:
            promo_service = PromoService(self.db)
            await promo_service.increment_usage_atomic(promo_obj.id)

        await self.db.commit()
        await self.db.refresh(new_order)
        return Order.model_validate(new_order)

    async def preview_order(
        self,
        cart_id: UUID,
        promo_code: Optional[str] = None,
        user_id: Optional[UUID] = None,
    ) -> dict:
        """Compute a preview (subtotal, discount, tax, total, items) without persisting."""
        # Fetch cart and items
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

        if not cart.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Cart is empty"
            )

        subtotal_cents = 0
        items = []
        for cart_item in cart.items:
            if not cart_item.product:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product for cart item {cart_item.id} no longer available",
                )
            line_total_cents = cart_item.quantity * cart_item.product.price_cents
            subtotal_cents += line_total_cents
            items.append(
                {
                    "product_id": str(cart_item.product.id),
                    "product_name": cart_item.product.name,
                    "quantity": cart_item.quantity,
                    "unit_price_cents": cart_item.product.price_cents,
                    "total_price_cents": line_total_cents,
                }
            )

        # Apply promo (reuse PromoService)
        discount_cents = 0
        applied_snapshot = None
        if promo_code:
            promo_service = PromoService(self.db)
            promo_result = await promo_service.validate_and_compute(
                promo_code, subtotal_cents, user_id
            )
            discount_cents = promo_result.get("discount_cents", 0)
            applied_snapshot = promo_result.get("snapshot")

        taxable = subtotal_cents - discount_cents
        tax_cents = int(taxable * TAX_RATE)
        total_cents = subtotal_cents - discount_cents + tax_cents

        return {
            "subtotal_cents": subtotal_cents,
            "discount_cents": discount_cents,
            "tax_cents": tax_cents,
            "total_cents": total_cents,
            "applied_discounts_snapshot": applied_snapshot,
            "items": items,
        }

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
        user_id: Optional[UUID],
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

        if user_id is not None and order.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Order does not belong to the user",
            )

        if order.version != version:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Order has been modified by another process. Please refresh and try again.",
            )

        # Validate via centralized state engine
        try:
            validate_transition_or_raise(order.status, new_status)
        except ValueError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

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

    async def get_session_orders(
        self,
        session_id: str,
        skip: int = 0,
        limit: int = 20,
    ) -> List[Order]:
        """Retrieve orders for a specific session with pagination."""
        if not session_id or len(session_id) < 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid session ID",
            )

        stmt = (
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.session_id == session_id)
            .order_by(Order.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        orders = result.scalars().all()
        return list(orders)
