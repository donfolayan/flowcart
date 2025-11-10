import logging
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.cart import Cart
from app.models.cart_item import CartItem

logger = logging.getLogger(__name__)


async def _add_item_to_cart(
    db: AsyncSession,
    variant_id: UUID,
    cart: Cart,
    product_id: UUID,
    quantity: int = 1,
    commit: bool = True,
    max_retries: int = 3,
) -> CartItem:
    """Add item to cart or update quantity if it exists.

    Retries on IntegrityError caused by concurrent inserts.
    Does not log DB internals to clients; logs them for diagnostics.
    """
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than zero",
        )

    last_exc: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            stmt = (
                select(CartItem)
                .where(CartItem.cart_id == cart.id, CartItem.variant_id == variant_id)
                .options(selectinload(CartItem.product))
                .with_for_update()
            )
            result = await db.execute(stmt)
            q: Optional[CartItem] = result.scalars().one_or_none()

            if q:
                q.quantity += quantity
                db.add(q)
            else:
                q = CartItem(
                    cart_id=cart.id,
                    variant_id=variant_id,
                    product_id=product_id,
                    quantity=quantity,
                )
                db.add(q)

            # bump cart version; ensure cart exists in DB scope
            if cart is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
                )
            cart.version += 1
            db.add(cart)

            await db.flush()

            if commit:
                await db.commit()

            # Refresh the instance; if refresh fails, defensively re-query
            try:
                await db.refresh(q)
            except Exception:
                if getattr(q, "id", None) is not None:
                    re_stmt = (
                        select(CartItem)
                        .where(CartItem.id == q.id)
                        .options(selectinload(CartItem.product))
                    )
                    re_res = await db.execute(re_stmt)
                    q = re_res.scalars().one_or_none()

            return q

        except IntegrityError as e:
            last_exc = e
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(
                "IntegrityError adding cart item (attempt %d/%d): %s",
                attempt,
                max_retries,
                getattr(e, "orig", e),
            )
            # final attempt -> return friendly error
            if attempt == max_retries:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to add item to cart due to concurrent update. Please retry.",
                )
            # otherwise retry loop

        except Exception as e:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.exception("Unexpected error adding item to cart: %s", e)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    # should not reach here
    logger.error("Exhausted retries adding item to cart: %s", last_exc)
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not add item to cart",
    )


async def _update_cart_item(
    db: AsyncSession,
    cart_item: CartItem,
    quantity: Optional[int] = None,
    commit: bool = True,
) -> Optional[CartItem]:
    """Update cart item quantity. If quantity is 0 the item is removed.
    Returns updated CartItem or None when item was deleted.
    """
    try:
        if quantity is None:
            return cart_item

        if quantity < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Quantity must be non-negative",
            )

        # Delete when quantity == 0
        if quantity == 0:
            await db.delete(cart_item)

            cart = await db.get(Cart, cart_item.cart_id)
            if cart is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
                )
            cart.version += 1
            db.add(cart)

            await db.flush()
            if commit:
                await db.commit()
            return None

        # positive quantity -> update
        cart_item.quantity = quantity
        db.add(cart_item)

        cart = await db.get(Cart, cart_item.cart_id)
        if cart is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
            )
        cart.version += 1
        db.add(cart)

        await db.flush()
        if commit:
            await db.commit()

        try:
            await db.refresh(cart_item)
        except Exception:
            # re-query defensively
            if getattr(cart_item, "id", None):
                re_stmt = select(CartItem).where(CartItem.id == cart_item.id)
                re_res = await db.execute(re_stmt)
                cart_item = re_res.scalars().one_or_none()

        return cart_item

    except IntegrityError as e:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.warning("IntegrityError updating cart item: %s", getattr(e, "orig", e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to update cart item"
        )

    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.exception("Unexpected error updating cart item: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


async def _merge_guest_cart(
    db: AsyncSession,
    cart: Cart,
    session_id: str,
    user_id: UUID,
) -> Cart:
    """Merge guest cart into user's cart. Commits once at the end."""
    try:
        stmt = (
            select(Cart)
            .where(
                Cart.session_id == session_id,
                Cart.user_id.is_(None),
                Cart.status == "active",
            )
            .options(selectinload(Cart.items))
            .with_for_update()
        )
        result = await db.execute(stmt)
        guest_cart: Optional[Cart] = result.scalars().one_or_none()

        if not guest_cart:
            return cart

        for item in guest_cart.items:
            await _add_item_to_cart(
                db=db,
                variant_id=item.variant_id,  # type: ignore
                cart=cart,
                product_id=item.product_id,
                quantity=item.quantity,
                commit=False,
            )

        # Remove guest cart and bump version once
        await db.delete(guest_cart)
        cart.version += 1
        db.add(cart)

        await db.flush()
        await db.commit()
        try:
            await db.refresh(cart)
        except Exception:
            # defensive reload
            if getattr(cart, "id", None):
                re_stmt = (
                    select(Cart)
                    .where(Cart.id == cart.id)
                    .options(selectinload(Cart.items))
                )
                re_res = await db.execute(re_stmt)
                cart = re_res.scalars().one_or_none()

        return cart

    except IntegrityError as e:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.warning("IntegrityError merging guest cart: %s", getattr(e, "orig", e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Failed to merge guest cart"
        )

    except Exception as e:
        try:
            await db.rollback()
        except Exception:
            pass
        logger.exception("Unexpected error merging guest cart: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
    return cart
