from uuid import UUID
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User

async def get_user_by_email(
    email: str,
    db: AsyncSession,
) -> Optional[User]:
    from sqlalchemy import func

    stmt = select(User).where(func.lower(User.email) == email.lower())
    res = await db.execute(stmt)
    user: Optional[User] = res.scalars().one_or_none()
    return user


async def get_user_by_id(db: AsyncSession, user_id: UUID) -> Optional[User]:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalars().unique().first()
