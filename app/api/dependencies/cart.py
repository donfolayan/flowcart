from uuid import UUID
from typing import Optional
from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.permissions import get_current_user_optional
from app.api.dependencies.session import get_session_id
from app.models.cart import Cart
from app.services.cart import CartService



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
) -> Cart | None:
    """Retrieve existing cart for user/session or create a new one."""
    service = CartService(db)
    return await service.get_or_create_cart(user_id=user_id, session_id=session_id)
