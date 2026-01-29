from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
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