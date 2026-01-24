from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from jose import JWTError
from uuid import UUID
from app.core.config import config
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token, RefreshTokenRequest
from app.core.jwt import decode_refresh_token
from app.db.session import get_session
from app.models.user import User
from app.core.security import hash_password, verify_password
from app.core.jwt import create_access_token, create_refresh_token
from app.schemas.email import VerifyEmailRequest, ResendVerificationRequest
from app.core.logs.logging_utils import get_logger
from app.util.email import send_and_save_verification_email

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token)
async def register_user(
    payload: UserCreate, db: AsyncSession = Depends(get_session)
) -> Token:
    stmt = select(User).where(User.email == payload.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    new_user = User(
        username=payload.username,
        email=payload.email,
        hashed_password=hash_password(payload.password),
    )

    db.add(new_user)
    await db.flush()

    # Send verification email (generates token, saves to DB, sends email)
    await send_and_save_verification_email(new_user, db, app_url=config.FRONTEND_URL)

    access_token = create_access_token({"sub": str(new_user.id)})
    refresh_token = create_refresh_token({"sub": str(new_user.id)})

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/login", response_model=Token)
async def login_user(
    payload: UserLogin, db: AsyncSession = Depends(get_session)
) -> Token:
    query = select(User)

    if payload.email:
        query = query.where(User.email == payload.email)
    else:
        query = query.where(User.username == payload.username)

    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
        )

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    data: RefreshTokenRequest, db: AsyncSession = Depends(get_session)
) -> Token:
    try:
        payload = decode_refresh_token(data.refresh_token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    user_id_value = payload.get("sub")

    if not user_id_value:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify user still exists
    user = await db.get(User, UUID(str(user_id_value)))

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": str(user_id_value)})
    new_refresh_token = create_refresh_token({"sub": str(user_id_value)})
    return Token(
        access_token=access_token, refresh_token=new_refresh_token, token_type="bearer"
    )


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest, db: AsyncSession = Depends(get_session)
):
    query = select(User).where(User.verification_token == payload.token)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.info(
            "Email verification failed - invalid token",
            extra={"token": payload.token},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid verification token"
        )

    if user.is_verified:
        return {"message": "Email already verified"}

    if user.verification_token_expiry and user.verification_token_expiry < datetime.now(
        timezone.utc
    ):
        logger.info(
            "Email verification failed - token expired",
            extra={"token": payload.token},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token has expired",
        )

    user.is_verified = True
    user.verification_token = None
    user.verification_token_expiry = None
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"message": "Email verified successfully"}


@router.post("/resend-verification-email")
async def resend_verification_email(
    payload: ResendVerificationRequest, db: AsyncSession = Depends(get_session)
):
    query = select(User).where(User.email == payload.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()

    if not user:
        logger.info(
            "Resend verification email failed - email not found",
            extra={"email": payload.email},
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Email not found"
        )

    if user.is_verified:
        return {"message": "Email already verified"}

    # Send verification email (generates token, saves to DB, sends email)
    await send_and_save_verification_email(user, db, app_url=config.FRONTEND_URL)

    return {"message": "Verification email resent successfully"}