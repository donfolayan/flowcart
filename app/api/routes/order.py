# from fastapi import APIRouter, Depends, status, HTTPException, Response
# from typing import List
# from uuid import UUID
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.exc import IntegrityError

# from app.db.session import get_session
# from app.db.user import get_user_by_id
# from app.models.order import Order
# from app.schemas.order import OrderCreate, OrderUpdate, OrderResponse

# router = APIRouter(prefix="/orders", tags=["orders"])


# @router.post(
#     "/",
#     response_model=OrderResponse,
#     status_code=status.HTTP_201_CREATED,
#     description="Create a new order from a cart",
# )
# async def create_order_from_cart(
#     payload: OrderCreate,
#     db: AsyncSession = Depends(get_session),
