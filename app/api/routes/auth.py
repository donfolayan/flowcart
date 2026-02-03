from datetime import datetime, timezone
import hashlib
from fastapi import APIRouter, Depends, HTTPException, status, Request
from jose import JWTError
from uuid import UUID
from app.core.config import config
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token, RefreshTokenRequest
from app.core.jwt import decode_refresh_token, get_refresh_token_expiry
from app.db.session import get_session
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.core.security import hash_password, verify_password, get_current_user
from app.core.jwt import create_access_token, create_refresh_token
from app.schemas.email import VerifyEmailRequest, ResendVerificationRequest
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.core.logs.logging_utils import get_logger
from app.util.email import send_and_save_verification_email, send_password_reset_email
from app.util.tokens import generate_password_reset_token, create_password_reset_token_expiry

logger = get_logger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])

limiter = Limiter(key_func=get_remote_address)

def get_device_id(request: Request) -> str:
    """Generate a device ID from user-agent and IP."""
    user_agent = request.headers.get("user-agent", "unknown")
    # Use a hash of user-agent for privacy
    return hashlib.sha256(user_agent.encode()).hexdigest()[:32]


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_and_store_refresh_token(
    db: AsyncSession,
    user_id: UUID,
    device_id: str,
) -> tuple[RefreshToken, str]:
    """
    Create a refresh token record in DB and return the JWT.
    
    Revokes any existing token for the same device before creating a new one.
    
    Returns:
        Tuple of (RefreshToken record, JWT string)
    """
    # Revoke existing token for this device
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == user_id,
            RefreshToken.device_id == device_id,
            RefreshToken.is_revoked.is_(False),
        )
        .values(is_revoked=True)
    )
    
    # Create new token record
    token_record = RefreshToken(
        user_id=user_id,
        device_id=device_id,
        token_hash="",  # Will be updated after JWT creation
        expires_at=get_refresh_token_expiry(),
    )
    db.add(token_record)
    await db.flush()  # Get the ID
    
    # Create the JWT with the token record ID
    jwt_token = create_refresh_token(
        data={"sub": str(user_id)},
        token_id=token_record.id,
    )
    
    # Store hash of the JWT for verification
    token_record.token_hash = hash_token(jwt_token)
    await db.flush()
    
    return token_record, jwt_token


@router.post("/register", response_model=Token)
async def register_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_session),
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

    # Create DB-backed refresh token
    device_id = get_device_id(request)
    _, refresh_token = await create_and_store_refresh_token(db, new_user.id, device_id)
    
    access_token = create_access_token({"sub": str(new_user.id)})
    await db.commit()

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_user(
    payload: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_session),
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

    # Create DB-backed refresh token (revokes old token for this device)
    device_id = get_device_id(request)
    _, refresh_token = await create_and_store_refresh_token(db, user.id, device_id)
    
    access_token = create_access_token({"sub": str(user.id)})
    await db.commit()

    return Token(
        access_token=access_token, refresh_token=refresh_token, token_type="bearer"
    )


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Token:
    """
    Refresh access token using a valid refresh token.
    
    The refresh token must:
    - Be a valid JWT
    - Exist in DB (by jti)
    - Not be revoked
    - Not be expired
    """
    try:
        payload = decode_refresh_token(data.refresh_token)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    
    user_id_value = payload.get("sub")
    token_id = payload.get("jti")

    if not user_id_value or not token_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Look up token in DB
    token_record = await db.get(RefreshToken, UUID(token_id))
    
    if not token_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate token hash matches
    if token_record.token_hash != hash_token(data.refresh_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token mismatch",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check token is valid
    if not token_record.is_valid():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token revoked or expired",
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

    # Update last_used_at
    token_record.last_used_at = datetime.now(timezone.utc)
    
    # Issue new access token (keep same refresh token)
    access_token = create_access_token({"sub": str(user_id_value)})
    await db.commit()
    
    return Token(
        access_token=access_token,
        refresh_token=data.refresh_token,  # Return same refresh token
        token_type="bearer",
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


@router.post("/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: AsyncSession = Depends(get_session)):
    query = select(User).where(User.email == payload.email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user:
        return {"message": f"If the {User.email} exists, a password reset link has been sent."}
    
    token = generate_password_reset_token()
    expiry = create_password_reset_token_expiry(hours=1)
    
    user.password_reset_token = token
    user.password_reset_token_expiry = expiry
    
    await db.commit()
    await send_password_reset_email(user.email, token, app_url=config.FRONTEND_URL)
    return {"message": f"If the {User.email} exists, a password reset link has been sent."}

@router.post("/reset-password")
async def reset_password(payload: ResetPasswordRequest, db: AsyncSession = Depends(get_session)):
    query = select(User).where(User.password_reset_token == payload.token)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if not user or not user.password_reset_token_expiry or user.password_reset_token_expiry < datetime.now(timezone.utc):
        logger.info(
            "Password reset failed - invalid or expired token",
            extra={"token": payload.token},
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired password reset token"
        )
    
    user.hashed_password = hash_password(payload.new_password)
    user.password_reset_token = None
    user.password_reset_token_expiry = None
    await db.commit()
    await db.refresh(user)
    
    return {"message": "Password has been reset successfully"}


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Logout from current device by revoking the refresh token.
    
    After logout, the refresh token will no longer work.
    The access token remains valid until it expires (short-lived).
    """
    try:
        payload = decode_refresh_token(data.refresh_token)
    except JWTError:
        # Token is invalid, consider it already logged out
        return {"message": "Logged out successfully"}
    
    token_id = payload.get("jti")
    if token_id:
        token_record = await db.get(RefreshToken, UUID(token_id))
        if token_record and not token_record.is_revoked:
            token_record.is_revoked = True
            await db.commit()
    
    return {"message": "Logged out successfully"}


@router.post("/logout-all")
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Logout from all devices by revoking all refresh tokens.
    
    Requires authentication (access token in header).
    """
    await db.execute(
        update(RefreshToken)
        .where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked.is_(False),
        )
        .values(is_revoked=True)
    )
    await db.commit()
    
    logger.info(
        "User logged out from all devices",
        extra={"user_id": str(current_user.id)},
    )
    
    return {"message": "Logged out from all devices"}


@router.get("/sessions")
async def list_active_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    List all active sessions (devices) for the current user.
    
    Returns a list of devices with their last activity.
    """
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == current_user.id,
        RefreshToken.is_revoked.is_(False),
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()
    
    sessions = [
        {
            "id": str(token.id),
            "device_id": token.device_id,
            "created_at": token.created_at.isoformat() if token.created_at else None,
            "last_used_at": token.last_used_at.isoformat() if token.last_used_at else None,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
        }
        for token in tokens
    ]
    
    return {"sessions": sessions, "count": len(sessions)}


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Revoke a specific session by its ID.
    
    Useful for remotely logging out a device.
    """
    token_record = await db.get(RefreshToken, session_id)
    
    if not token_record or token_record.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )
    
    if token_record.is_revoked:
        return {"message": "Session already revoked"}
    
    token_record.is_revoked = True
    await db.commit()
    
    return {"message": "Session revoked successfully"}