from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError

from app.models.user import User
from app.core.security import get_current_user, bearer_scheme
from app.core.jwt import decode_access_token
from app.db.session import get_session
from app.services.user import UserService


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if not getattr(user, "is_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    """Return the current user if a valid Bearer token is provided; otherwise None.

    - No credentials or wrong scheme -> None
    - Invalid/expired token -> None
    - Missing/invalid user in DB -> None
    """
    if not credentials or credentials.scheme.lower() != "bearer":
        return None

    token = credentials.credentials
    try:
        payload = decode_access_token(token)
    except JWTError:
        return None

    user_id_value = payload.get("sub")
    if not user_id_value:
        return None

    try:
        user_id = UUID(str(user_id_value))
    except Exception:
        return None

    service = UserService(db)
    user = await service.get_by_id(user_id)
    return user
