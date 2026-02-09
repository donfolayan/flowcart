from typing import Optional
from uuid import UUID
from decimal import Decimal
from sqlalchemy import and_, select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from fastapi import HTTPException, status
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.models.product import Product
from app.models.user import User
from app.core.logs.logging_utils import get_logger
from app.enums.currency_enums import CurrencyEnum

logger = get_logger("app.cart")


async def _add_item_to_cart(
    db: AsyncSession,
    variant_id: Optional[UUID],
    cart: Cart,
    product_id: UUID,
    quantity: int = 1,
    commit: bool = True,
    max_retries: int = 3,
) -> Optional[CartItem]:
    """Add item to cart. If item with same variant_id exists, increments quantity."""
    #Quantity Check
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Quantity must be > 0"
        )

    # Cart Existence Check
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
        logger.info(
            "Attempted to add product with variants without specifying variant_id",
            extra={"product_id": str(product_id), "cart_id": str(cart.id)},
        )
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
        # variant_id is None, match by product_id and ensure variant_id is NULL
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

                # recompute and persist cart subtotal
                try:
                    sum_stmt = select(func.coalesce(func.sum(CartItem.line_total), 0)).where(
                        CartItem.cart_id == cart.id
                    )
                    subtotal = (await db.execute(sum_stmt)).scalar_one()
                    await db.execute(update(Cart).where(Cart.id == cart.id).values(subtotal=subtotal))
                    await db.commit()
                except IntegrityError:
                    logger.exception("Integrity error persisting cart subtotal after update")
                except Exception:
                    logger.exception("Failed to persist cart subtotal after update")

                # return the updated item
                q_stmt = select(CartItem).where(cartitem_where_clause())
                q_res = await db.execute(q_stmt)
                item = q_res.scalars().one_or_none()
                return item


            # determine unit price from variant (if present) or product base_price
            unit_price: Optional[Decimal] = None
            chosen_variant = None
            if variant_id is not None:
                for v in getattr(product, "variants", []) or []:
                    if getattr(v, "id", None) == variant_id:
                        chosen_variant = v
                        break
                if chosen_variant is not None and getattr(chosen_variant, "price", None) is not None:
                    unit_price = Decimal(chosen_variant.price)
            if unit_price is None:
                base_price = getattr(product, "base_price", None)
                unit_price = Decimal(base_price) if base_price is not None else None

            if unit_price is None:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Price unavailable for product or variant",
                )
                
            product_snapshot = {
                "id": str(product.id),
                "name": product.name,
                "sku": getattr(product, "sku", None),
                "price": str(unit_price),
                "attributes": getattr(product, "attributes", {}),
            }

            # Construct the CartItem using server-trusted values only.
            new_item = CartItem(
                cart_id=cart.id,
                variant_id=variant_id,  # may be None
                product_id=product_id,
                quantity=quantity,
                product_name=product.name,
                product_snapshot=product_snapshot,
                unit_price_currency=CurrencyEnum.USD,
                unit_price=unit_price,
                tax_amount=Decimal("0.00"),
                discount_amount=Decimal("0.00"),
            )

            # Add the new item to the session and flush so `new_item.id`
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

            # persist subtotal so Cart.total
            try:
                sum_stmt = select(func.coalesce(func.sum(CartItem.line_total), 0)).where(
                    CartItem.cart_id == cart.id
                )
                subtotal = (await db.execute(sum_stmt)).scalar_one()
                await db.execute(update(Cart).where(Cart.id == cart.id).values(subtotal=subtotal))
                await db.commit()
            except Exception:
                logger.exception("Failed to persist cart subtotal after insert")

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
                refreshed_item = re_res.scalars().one_or_none()
                if refreshed_item is not None:
                    cart_item = refreshed_item

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
                refreshed_cart = re_res.scalars().one_or_none()
                if refreshed_cart is not None:
                    cart = refreshed_cart

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


class CartService:
    """Business logic for cart and cart items."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_or_create_cart(
        self,
        user_id: Optional[UUID | User],
        session_id: str,
    ) -> Cart | None:
        uid: Optional[User | UUID] = user_id
        if isinstance(uid, User):
            uid = getattr(uid, "id", None)

        if uid:
            stmt = select(Cart).where(Cart.user_id == uid, Cart.status == "active")
        else:
            stmt = select(Cart).where(
                Cart.session_id == session_id, Cart.status == "active"
            )

        result = await self.db.execute(stmt)
        cart = result.scalars().first()
        if cart:
            return cart
        cart = Cart(user_id=uid, session_id=session_id, status="active", version=1)
        self.db.add(cart)
        try:
            await self.db.commit()
            await self.db.refresh(cart)
            return cart
        except IntegrityError:
            logger.debug(
                "IntegrityError on cart creation, likely due to race condition. Retrying fetch.",
                extra={
                    "user_id": str(uid) if uid else None,
                    "session_id": session_id,
                },
            )
            try:
                await self.db.rollback()
            except Exception:
                pass
            if uid:
                stmt = select(Cart).where(Cart.user_id == uid, Cart.status == "active")
            else:
                stmt = select(Cart).where(
                    Cart.session_id == session_id, Cart.status == "active"
                )
            result = await self.db.execute(stmt)
            return result.scalars().first()
        except Exception as e:
            await self.db.rollback()
            logger.exception(
                "Failed to create or retrieve cart",
                extra={
                    "user_id": str(uid) if uid else None,
                    "session_id": session_id,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Internal Server Error - {str(e)}",
            ) from e

    async def add_item_to_cart(
        self,
        cart: Cart | None,
        payload,
    ) -> Cart:
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve cart",
            )

        if getattr(cart, "status", None) != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify non-active cart",
            )

        try:
            await _add_item_to_cart(
                db=self.db,
                variant_id=payload.variant_id,
                cart=cart,
                product_id=payload.product_id,
                quantity=payload.quantity,
                commit=True,
            )

            try:
                _opt = selectinload(Cart.items)
            except InvalidRequestError:
                _opt = None
            stmt = select(Cart).where(Cart.id == cart.id)
            if _opt is not None:
                stmt = stmt.options(_opt)
            res = await self.db.execute(stmt)
            refreshed_cart = res.scalars().one_or_none()

            if not refreshed_cart:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cart not found after adding item",
                )
            return refreshed_cart
        except IntegrityError as ie:
            logger.debug(
                "IntegrityError when adding item to cart",
                extra={"payload": payload.model_dump()},
            )
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error when adding item to cart",
            ) from ie
        except HTTPException:
            raise
        except Exception as e:
            try:
                await self.db.rollback()
            except Exception:
                pass
            logger.exception(
                "Failed to add item to cart",
                extra={"payload": payload.model_dump()},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error when adding item to cart",
            ) from e

    async def update_cart_item(
        self,
        cart: Cart | None,
        item_id: UUID,
        payload,
    ) -> Cart:
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve cart",
            )

        if getattr(cart, "status", None) != "active":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify non-active cart",
            )
        try:
            stmt = select(CartItem).where(
                CartItem.id == item_id, CartItem.cart_id == cart.id
            )
            res = await self.db.execute(stmt)
            cart_item = res.scalars().one_or_none()

            if not cart_item:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cart item not found",
                )

            await _update_cart_item(
                db=self.db,
                cart_item=cart_item,
                quantity=payload.quantity,
                commit=True,
            )

            try:
                _opt = selectinload(Cart.items)
            except InvalidRequestError:
                _opt = None
            stmt = select(Cart).where(Cart.id == cart.id)
            if _opt is not None:
                stmt = stmt.options(_opt)
            res = await self.db.execute(stmt)
            refreshed_cart = res.scalars().one_or_none()

            if not refreshed_cart:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Cart item not found after update",
                )
            return refreshed_cart
        except IntegrityError as ie:
            try:
                await self.db.rollback()
            except Exception:
                pass
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Integrity error when updating cart item",
            ) from ie
        except HTTPException:
            raise
        except Exception as e:
            try:
                await self.db.rollback()
            except Exception:
                pass
            logger.exception(
                "Failed to update cart item",
                extra={"item_id": str(item_id), "payload": payload.model_dump()},
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal server error when updating cart item",
            ) from e

    async def delete_cart_item(self, cart: Cart | None, item_id: UUID) -> None:
        if not cart:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create or retrieve cart",
            )

        stmt = select(CartItem).where(
            CartItem.id == item_id, CartItem.cart_id == cart.id
        )
        cart_item = (await self.db.execute(stmt)).scalars().one_or_none()
        if not cart_item:
            raise HTTPException(404, "Cart item not found")
        await self.db.delete(cart_item)
        cart.version += 1
        await self.db.commit()
