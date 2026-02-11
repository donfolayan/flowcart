from uuid import UUID
from typing import Optional
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session
from app.schemas.cart import CartResponse
from app.api.dependencies.cart import get_or_create_cart
from app.schemas.cart_item import CartItemCreate, CartItemUpdate
from app.services.cart import CartService
from app.api.dependencies.session import get_or_create_session_id
from app.core.permissions import get_current_user_optional

router = APIRouter(prefix="/cart", tags=["Cart Items"])


@router.post(
    "/items",
    response_model=CartResponse,
    status_code=status.HTTP_201_CREATED,
    description="Add an item to the cart",
)
async def add_item_to_cart(
    payload: CartItemCreate,
    response: Response,
    db: AsyncSession = Depends(get_session),
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
):
    cart = await get_or_create_cart(db=db, user_id=user_id, session_id=session_id)
    service = CartService(db)
    cart = await service.add_item_to_cart(cart=cart, payload=payload)

    response.headers["Location"] = f"/cart/{cart.id}"
    return CartResponse.model_validate(cart)


@router.patch(
    "/",
    response_model=CartResponse,
    status_code=status.HTTP_200_OK,
    description="Update an item in the cart",
)
async def patch_cart_items(
    item_id: UUID,
    payload: CartItemUpdate,
    db: AsyncSession = Depends(get_session),
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
) -> CartResponse:
    cart = await get_or_create_cart(db=db, user_id=user_id, session_id=session_id)
    service = CartService(db)
    cart = await service.update_cart_item(cart=cart, item_id=item_id, payload=payload)

    return CartResponse.model_validate(cart)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_cart_item(
    item_id: UUID,
    db: AsyncSession = Depends(get_session),
    user_id: Optional[UUID] = Depends(get_current_user_optional),
    session_id: str = Depends(get_or_create_session_id),
):
    cart = await get_or_create_cart(db=db, user_id=user_id, session_id=session_id)
    service = CartService(db)
    await service.delete_cart_item(cart=cart, item_id=item_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
