from uuid import UUID
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.models.cart import Cart


async def get_cart_or_404(
    cart_id: UUID,
    db: AsyncSession,
) -> Cart:
    """Retrieve cart by ID or raise 404."""
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id)
    )
    cart = result.scalars().one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )
    return cart


async def get_or_create_cart(
    db: AsyncSession,
    user_id: Optional[UUID],
    session_id: str,
) -> Cart:
    """Retrieve existing cart for user/session or create a new one."""
    if user_id:
        stmt = select(Cart).where(Cart.user_id == user_id, Cart.status == "active")
    else:
        stmt = select(Cart).where(
            Cart.session_id == session_id, Cart.status == "active"
        )

    result = await db.execute(stmt)
    cart = result.scalars().first()
    if cart:
        return cart

    cart = Cart(user_id=user_id, session_id=session_id, status="active", version=1)
    db.add(cart)
    try:
        await db.commit()
        await db.refresh(cart)
        return cart
    except IntegrityError:
        try:
            await db.rollback()
        except Exception:
            pass

        if user_id:
            stmt = select(Cart).where(Cart.user_id == user_id, Cart.status == "active")
        else:
            stmt = select(Cart).where(
                Cart.session_id == session_id, Cart.status == "active"
            )
        result = await db.execute(stmt)
        return result.scalars().first()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        ) from e
