from fastapi import Depends, HTTPException
from app.models.user import User
from app.core.security import get_current_user


async def require_admin(get_current_user: User = Depends(get_current_user)) -> User:
    if not getattr(get_current_user, "is_admin", False):
        raise HTTPException(
            status_code=403,
            detail="Admin privileges required",
        )
    return get_current_user
