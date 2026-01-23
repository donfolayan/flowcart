from typing import Optional
from uuid import UUID
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.core.logging_utils import get_logger

logger = get_logger("app.cart")


async def _add_item_to_cart(
    db: AsyncSession,
    variant_id: Optional[UUID],
    cart: Cart,
    product_id: UUID,
    quantity: int = 1,
    commit: bool = True,
    max_retries: int = 3,
) -> CartItem:
    """Add item to cart. If item with same variant_id exists, increments quantity."""
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be > 0"
        )

    if cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
        )

    prod_stmt = (
        select(Product)
        .where(Product.id == product_id)
        .options(selectinload(Product.variants))
    )
    prod_res = await db.execute(prod_stmt)
    product: Optional[Product] = prod_res.scalars().one_or_none()
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )

    has_variants = bool(getattr(product, "variants", None))
    if has_variants and variant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This product requires a variant_id to add to cart",
        )

    def cartitem_where_clause():
        if variant_id is not None:
            return and_(
                CartItem.cart_id == cart.id,
                CartItem.variant_id == variant_id,
            )
        # variant_id is None -> match by product_id and ensure variant_id is NULL
        return and_(
            CartItem.cart_id == cart.id,
            CartItem.product_id == product_id,
            CartItem.variant_id.is_(None),
        )

    refreshed_cart = await db.get(Cart, cart.id)
    if refreshed_cart is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
        )
    old_cart_version = refreshed_cart.version

    last_exc = None
    for attempt in range(1, max_retries + 1):
        try:
            # Try to update existing CartItem (increment quantity)
            upd_stmt = (
                update(CartItem)
                .where(cartitem_where_clause())
                .values(quantity=(CartItem.quantity + quantity))
                .returning(CartItem.id)
            )
            res = await db.execute(upd_stmt)
            updated_row = res.scalar_one_or_none()

            if updated_row:
                # bump cart version atomically
                cart_version_stmt = (
                    update(Cart)
                    .where(Cart.id == cart.id, Cart.version == old_cart_version)
                    .values(version=(Cart.version + 1))
                    .returning(Cart.version)
                )
                ver_res = await db.execute(cart_version_stmt)
                new_version = ver_res.scalar_one_or_none()
                if new_version is None:
                    await db.rollback()
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Cart modified concurrently, please retry.",
                    )

                if commit:
                    await db.commit()

                # return the updated item
                q_stmt = select(CartItem).where(cartitem_where_clause())
                q_res = await db.execute(q_stmt)
                item = q_res.scalars().one_or_none()
                return item

            # No existing item -> create new one
            new_item = CartItem(
                cart_id=cart.id,
                variant_id=variant_id,  # may be None
                product_id=product_id,
                quantity=quantity,
            )
            db.add(new_item)

            await db.flush()

            # bump version
            cart_version_stmt = (
                update(Cart)
                .where(Cart.id == cart.id, Cart.version == old_cart_version)
                .values(version=(Cart.version + 1))
                .returning(Cart.version)
            )
            ver_res = await db.execute(cart_version_stmt)
            new_version = ver_res.scalar_one_or_none()
            if new_version is None:
                await db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cart modified concurrently, please retry.",
                )

            if commit:
                await db.commit()
            else:
                await db.flush()

            # attempt refresh, fallback to defensive query
            try:
                await db.refresh(new_item)
            except Exception:
                q_stmt = select(CartItem).where(
                    CartItem.id == getattr(new_item, "id", None)
                )
                q_res = await db.execute(q_stmt)
                new_item = q_res.scalars().one_or_none()

            return new_item

        except IntegrityError as e:
            last_exc = e
            try:
                await db.rollback()
            except Exception:
                pass
            logger.warning(
                "IntegrityError while adding item (attempt %d/%d): %s",
                attempt,
                max_retries,
                getattr(e, "orig", e),
            )

            if attempt == max_retries:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to add item due to concurrent update; please retry.",
                )

            refreshed_cart = await db.get(Cart, cart.id)
            if refreshed_cart is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Cart not found"
                )
            old_cart_version = refreshed_cart.version

        except HTTPException:
            raise

        except Exception as e:
            last_exc = e
            try:
                await db.rollback()
            except Exception:
                pass
            logger.exception(
                "Unexpected error in _add_item_to_cart: %s", e, exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error",
            )

    # Exhausted retries
    logger.error("Exhausted retries in _add_item_to_cart: %s", last_exc)
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
        logger.debug("IntegrityError updating cart item: %s", getattr(e, "orig", e))
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
        logger.debug("IntegrityError merging guest cart: %s", getattr(e, "orig", e))
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
