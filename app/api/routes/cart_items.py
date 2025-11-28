from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.cart import Cart
from app.models.cart_item import CartItem
from app.schemas.cart import CartResponse
from app.api.dependencies.cart import get_cart_or_404
from app.schemas.cart_item import CartItemCreate, CartItemUpdate
from app.services.cart import _add_item_to_cart, _update_cart_item

router = APIRouter(prefix="/cart/{cart_id}/items", tags=["cart-items"])


@router.post(
    "/",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    description="Add an item to the cart",
)
async def add_item_to_cart(
    cart_id: UUID,
    payload: CartItemCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
):
    cart: Cart = await get_cart_or_404(cart_id, db)

    if getattr(cart, "status", None) != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify non-active cart",
        )

    try:
        await _add_item_to_cart(
            db=db,
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
        res = await db.execute(stmt)
        cart = res.scalars().one_or_none()

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart not found after adding item",
            )
    except IntegrityError as ie:
        try:
            await db.rollback()
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
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error when adding item to cart",
        ) from e

    response.headers["Location"] = f"/cart/{cart.id}"
    return CartResponse.model_validate(cart)


@router.patch(
    "/",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    description="Update an item in the cart",
)
async def patch_cart_items(
    cart_id: UUID,
    item_id: UUID,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_session),
) -> CartResponse:
    cart: Cart = await get_cart_or_404(cart_id, db)

    if getattr(cart, "status", None) != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify non-active cart",
        )
    try:
        stmt = select(CartItem).where(
            CartItem.id == item_id, CartItem.cart_id == cart.id
        )
        res = await db.execute(stmt)
        cart_item = res.scalars().one_or_none()

        if not cart_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found",
            )

        # update the item

        await _update_cart_item(
            db=db,
            cart_item=cart_item,
            quantity=payload.quantity,
            commit=True,
        )

        # reload cart

        try:
            _opt = selectinload(Cart.items)
        except InvalidRequestError:
            _opt = None
        stmt = select(Cart).where(Cart.id == cart.id)
        if _opt is not None:
            stmt = stmt.options(_opt)
        res = await db.execute(stmt)
        cart = res.scalars().one_or_none()

        if not cart:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cart item not found after update",
            )
    except IntegrityError as ie:
        try:
            await db.rollback()
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
            await db.rollback()
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error when updating cart item",
        ) from e

    return CartResponse.model_validate(cart)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(
    cart_id: UUID, item_id: UUID, db: AsyncSession = Depends(get_session)
):
    cart = await get_cart_or_404(cart_id, db)
    stmt = select(CartItem).where(CartItem.id == item_id, CartItem.cart_id == cart.id)
    cart_item = (await db.execute(stmt)).scalars().one_or_none()
    if not cart_item:
        raise HTTPException(404, "Cart item not found")
    await db.delete(cart_item)
    cart.version += 1
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
