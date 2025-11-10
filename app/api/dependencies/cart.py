from uuid import UUID
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
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
