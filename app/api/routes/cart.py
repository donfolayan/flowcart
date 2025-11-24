from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.cart import Cart
from app.schemas.cart import CartResponse
from app.api.dependencies.cart import get_cart_or_404, get_or_create_cart
from app.api.dependencies.session import get_or_create_session_id
from app.core.permissions import get_current_user_optional

router = APIRouter(prefix="/cart", tags=["cart"])


@router.get(
    "/{cart_id}",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    description="Retrieve a cart by its ID",
)
async def get_cart(
    cart_id: UUID,
    db: AsyncSession = Depends(get_session),
):
    cart: Cart = await get_cart_or_404(cart_id, db)
    return cart


@router.post(
    "/",
    response_model=CartResponse,
    description="Create a new cart",
    status_code=status.HTTP_201_CREATED,
)
async def create_cart(
    response: Response,
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
    db: AsyncSession = Depends(get_session),
):
    new_cart = await get_or_create_cart(
        db=db,
        user_id=user_id if user_id else None,
        session_id=session_id,
    )
    db.add(new_cart)
    try:
        await db.commit()
        await db.refresh(new_cart)
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error - {str(e)}",
        ) from e

    response.headers["Location"] = f"/cart/{new_cart.id}"
    return CartResponse.model_validate(new_cart)
