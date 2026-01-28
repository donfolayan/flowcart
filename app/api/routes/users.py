from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_session

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

@router.get("/me")
async def read_users_me():
    pass