from uuid import UUID
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.core.permissions import get_current_user_optional
from app.api.dependencies.session import get_session_id
from app.models.cart import Cart
from app.models.user import User
from app.core.logs.logging_utils import get_logger

logger = get_logger("app.cart")


async def get_cart_or_404(
    cart_id: UUID,
    db: AsyncSession,
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: Optional[str] = Depends(get_session_id),
) -> Cart:
    """Retrieve cart by ID and verify ownership (user or session)."""
    result = await db.execute(
        select(Cart).options(selectinload(Cart.items)).where(Cart.id == cart_id)
    )
    cart = result.scalars().one_or_none()
    if not cart:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart not found",
        )
    
    # Verify ownership: check user_id or session_id
    if user_id:
        if cart.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this cart",
            )
    elif session_id:
        if cart.session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this cart",
            )
    else:
        # Neither user_id nor session_id provided
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this cart",
        )
    
    return cart


async def get_or_create_cart(
    db: AsyncSession,
    user_id: Optional[UUID],
    session_id: str,
) -> Cart:
    """Retrieve existing cart for user/session or create a new one."""
    # `get_current_user_optional` may return a `User` instance or a UUID.
    uid: Optional[User | UUID] = user_id
    if isinstance(uid, User):
        uid = getattr(uid, "id", None)

    if uid:
        stmt = select(Cart).where(Cart.user_id == uid, Cart.status == "active")
    else:
        stmt = select(Cart).where(
            Cart.session_id == session_id, Cart.status == "active"
        )

    result = await db.execute(stmt)
    cart = result.scalars().first()
    if cart:
        return cart
    cart = Cart(user_id=uid, session_id=session_id, status="active", version=1)
    db.add(cart)
    try:
        await db.commit()
        await db.refresh(cart)
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
            await db.rollback()
        except Exception:
            pass
        if uid:
            stmt = select(Cart).where(Cart.user_id == uid, Cart.status == "active")
        else:
            stmt = select(Cart).where(
                Cart.session_id == session_id, Cart.status == "active"
            )
        result = await db.execute(stmt)
        return result.scalars().first()
    except Exception as e:
        await db.rollback()
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
