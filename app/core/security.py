import secrets
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from passlib.context import CryptContext
from app.db.session import get_session
from app.db.user import get_user_by_id
from app.models.user import User
from app.core.jwt import decode_access_token
from app.core.logs.logging_utils import get_logger

logger = get_logger("app.security")

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def generate_verification_token() -> str:
    return secrets.token_urlsafe(32)

def create_verification_token_expiry(hours: int = 24) -> datetime: #24hr expiry
    return datetime.now(timezone.utc) + timedelta(hours=hours)

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_session),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not Authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user_id_value = payload.get("sub")
    if not user_id_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        user_id = UUID(str(user_id_value))
    except Exception as e:
        logger.exception(
            "Invalid user id in token",
            extra={"user_id_value": str(user_id_value)},
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user id in token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    user = await get_user_by_id(db, user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    return user


async def get_user_by_email(
    email: str,
    db: AsyncSession = Depends(get_session),
) -> Optional[User]:
    stmt = select(User).where(User.email == email.lower())
    res = await db.execute(stmt)
    user: Optional[User] = res.scalars().one_or_none()
    return user