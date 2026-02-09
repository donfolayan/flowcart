from datetime import datetime, timezone
import hashlib
from uuid import UUID

from fastapi import HTTPException, status, Request
from jose import JWTError
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import config
from app.core.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    get_refresh_token_expiry,
)
from app.core.logs.logging_utils import get_logger
from app.core.security import hash_password, verify_password
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.schemas.email import ResendVerificationRequest, VerifyEmailRequest
from app.schemas.token import RefreshTokenRequest, Token
from app.schemas.user import UserCreate, UserLogin
from app.util.email import send_and_save_verification_email, send_password_reset_email
from app.util.tokens import (
    create_password_reset_token_expiry,
    generate_password_reset_token,
)

logger = get_logger(__name__)


def get_device_id(request: Request) -> str:
    """Generate a device ID from user-agent and IP."""
    user_agent = request.headers.get("user-agent", "unknown")
    # Use a hash of user-agent for privacy
    return hashlib.sha256(user_agent.encode()).hexdigest()[:32]


def hash_token(token: str) -> str:
    """Hash a token for secure storage."""
    return hashlib.sha256(token.encode()).hexdigest()


class AuthService:
    """Business logic for authentication and sessions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _create_and_store_refresh_token(
        self, user_id: UUID, device_id: str
    ) -> tuple[RefreshToken, str]:
        """
        Create a refresh token record in DB and return the JWT.

        Revokes any existing token for the same device before creating a new one.
        """
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.device_id == device_id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )

        token_record = RefreshToken(
            user_id=user_id,
            device_id=device_id,
            token_hash="",  # Will be updated after JWT creation
            expires_at=get_refresh_token_expiry(),
        )
        self.db.add(token_record)
        await self.db.flush()

        jwt_token = create_refresh_token(
            data={"sub": str(user_id)},
            token_id=token_record.id,
        )

        token_record.token_hash = hash_token(jwt_token)
        await self.db.flush()

        return token_record, jwt_token

    async def register(self, payload: UserCreate, request: Request) -> Token:
        stmt = select(User).where(User.email == payload.email)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        new_user = User(
            username=payload.username,
            email=payload.email,
            hashed_password=hash_password(payload.password),
        )

        self.db.add(new_user)
        await self.db.flush()

        await send_and_save_verification_email(
            new_user, self.db, app_url=config.FRONTEND_URL
        )

        device_id = get_device_id(request)
        _, refresh_token = await self._create_and_store_refresh_token(
            new_user.id, device_id
        )

        access_token = create_access_token({"sub": str(new_user.id)})
        await self.db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def login(self, payload: UserLogin, request: Request) -> Token:
        query = select(User)

        if payload.email:
            query = query.where(User.email == payload.email)
        else:
            query = query.where(User.username == payload.username)

        result = await self.db.execute(query)
        user = result.scalar_one_or_none()
        if not user or not verify_password(payload.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        device_id = get_device_id(request)
        _, refresh_token = await self._create_and_store_refresh_token(user.id, device_id)

        access_token = create_access_token({"sub": str(user.id)})
        await self.db.commit()

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )

    async def refresh_token(self, data: RefreshTokenRequest) -> Token:
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

        token_record = await self.db.get(RefreshToken, UUID(token_id))

        if not token_record:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token_record.token_hash != hash_token(data.refresh_token):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token mismatch",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not token_record.is_valid():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token revoked or expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = await self.db.get(User, UUID(str(user_id_value)))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token_record.last_used_at = datetime.now(timezone.utc)

        access_token = create_access_token({"sub": str(user_id_value)})
        await self.db.commit()

        return Token(
            access_token=access_token,
            refresh_token=data.refresh_token,
            token_type="bearer",
        )

    async def verify_email(self, payload: VerifyEmailRequest) -> dict:
        query = select(User).where(User.verification_token == payload.token)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            logger.info(
                "Email verification failed - invalid token",
                extra={"token": payload.token},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid verification token",
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
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return {"message": "Email verified successfully"}

    async def resend_verification_email(
        self, payload: ResendVerificationRequest
    ) -> dict:
        query = select(User).where(User.email == payload.email)
        result = await self.db.execute(query)
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

        await send_and_save_verification_email(
            user, self.db, app_url=config.FRONTEND_URL
        )

        return {"message": "Verification email resent successfully"}

    async def forgot_password(
        self, payload: ForgotPasswordRequest, request: Request
    ) -> dict:
        query = select(User).where(User.email == payload.email)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "message": f"If the {User.email} exists, a password reset link has been sent."
            }

        token = generate_password_reset_token()
        expiry = create_password_reset_token_expiry(hours=1)

        user.password_reset_token = token
        user.password_reset_token_expiry = expiry

        await self.db.commit()
        await send_password_reset_email(user.email, token, app_url=config.FRONTEND_URL)
        return {
            "message": f"If the {User.email} exists, a password reset link has been sent."
        }

    async def reset_password(self, payload: ResetPasswordRequest) -> dict:
        query = select(User).where(User.password_reset_token == payload.token)
        result = await self.db.execute(query)
        user = result.scalar_one_or_none()

        if (
            not user
            or not user.password_reset_token_expiry
            or user.password_reset_token_expiry < datetime.now(timezone.utc)
        ):
            logger.info(
                "Password reset failed - invalid or expired token",
                extra={"token": payload.token},
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired password reset token",
            )

        user.hashed_password = hash_password(payload.new_password)
        user.password_reset_token = None
        user.password_reset_token_expiry = None
        await self.db.commit()
        await self.db.refresh(user)

        return {"message": "Password has been reset successfully"}

    async def logout(self, data: RefreshTokenRequest) -> dict:
        try:
            payload = decode_refresh_token(data.refresh_token)
        except JWTError:
            return {"message": "Logged out successfully"}

        token_id = payload.get("jti")
        if token_id:
            token_record = await self.db.get(RefreshToken, UUID(token_id))
            if token_record and not token_record.is_revoked:
                token_record.is_revoked = True
                await self.db.commit()

        return {"message": "Logged out successfully"}

    async def logout_all_devices(self, current_user: User) -> dict:
        await self.db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == current_user.id,
                RefreshToken.is_revoked.is_(False),
            )
            .values(is_revoked=True)
        )
        await self.db.commit()

        logger.info(
            "User logged out from all devices",
            extra={"user_id": str(current_user.id)},
        )

        return {"message": "Logged out from all devices"}

    async def list_active_sessions(self, current_user: User) -> dict:
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == current_user.id,
            RefreshToken.is_revoked.is_(False),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        result = await self.db.execute(stmt)
        tokens = result.scalars().all()

        sessions = [
            {
                "id": str(token.id),
                "device_id": token.device_id,
                "created_at": token.created_at.isoformat()
                if token.created_at
                else None,
                "last_used_at": token.last_used_at.isoformat()
                if token.last_used_at
                else None,
                "expires_at": token.expires_at.isoformat()
                if token.expires_at
                else None,
            }
            for token in tokens
        ]

        return {"sessions": sessions, "count": len(sessions)}

    async def revoke_session(self, session_id: UUID, current_user: User) -> dict:
        token_record = await self.db.get(RefreshToken, session_id)

        if not token_record or token_record.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        if token_record.is_revoked:
            return {"message": "Session already revoked"}

        token_record.is_revoked = True
        await self.db.commit()

        return {"message": "Session revoked successfully"}
