from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.cart import Cart
from app.schemas.cart import CartResponse
from app.api.dependencies.cart import get_cart_or_404
from app.api.dependencies.session import get_or_create_session_id
from app.core.permissions import get_current_user_optional
from app.services.cart import CartService

router = APIRouter(prefix="/cart", tags=["Cart"])


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
    service = CartService(db)
    new_cart = await service.get_or_create_cart(
        user_id=user_id if user_id else None,
        session_id=session_id,
    )
    if not new_cart:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create or retrieve cart",
        )

    response.headers["Location"] = f"/cart/{new_cart.id}"
    return CartResponse.model_validate(new_cart)
