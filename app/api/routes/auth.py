from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.schemas.user import UserCreate, UserLogin
from app.schemas.token import Token, RefreshTokenRequest
from app.db.session import get_session
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.email import VerifyEmailRequest, ResendVerificationRequest
from app.schemas.auth import ForgotPasswordRequest, ResetPasswordRequest
from app.services.auth import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=Token)
@limiter.limit("3/minute")
async def register_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Token:
    service = AuthService(db)
    return await service.register(payload=payload, request=request)


@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login_user(
    payload: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Token:
    service = AuthService(db)
    return await service.login(payload=payload, request=request)


@router.post("/refresh", response_model=Token)
async def refresh_token_endpoint(
    data: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Token:
    service = AuthService(db)
    return await service.refresh_token(data=data)


@router.post("/verify-email")
async def verify_email(
    payload: VerifyEmailRequest, db: AsyncSession = Depends(get_session)
):
    service = AuthService(db)
    return await service.verify_email(payload=payload)


@router.post("/resend-verification-email")
async def resend_verification_email(
    payload: ResendVerificationRequest, db: AsyncSession = Depends(get_session)
):
    service = AuthService(db)
    return await service.resend_verification_email(payload=payload)


@router.post("/forgot-password")
@limiter.limit("3/minute")
async def forgot_password(
    request: Request,
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_session),
):
    service = AuthService(db)
    return await service.forgot_password(payload=payload, request=request)


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest, db: AsyncSession = Depends(get_session)
):
    service = AuthService(db)
    return await service.reset_password(payload=payload)


@router.post("/logout")
async def logout(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_session),
):
    service = AuthService(db)
    return await service.logout(data=data)


@router.post("/logout-all")
async def logout_all_devices(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = AuthService(db)
    return await service.logout_all_devices(current_user=current_user)


@router.get("/sessions")
async def list_active_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = AuthService(db)
    return await service.list_active_sessions(current_user=current_user)


@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    service = AuthService(db)
    return await service.revoke_session(
        session_id=session_id, current_user=current_user
    )
