from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from app.core.permissions import require_admin
from app.core.security import get_current_user, hash_password
from app.db.session import get_session, AsyncSession
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from sqlalchemy.exc import IntegrityError
from app.util.email import (
    generate_verification_token,
    create_verification_token_expiry,
    send_verification_email,
)
from app.core.logs.logging_utils import get_logger


logger = get_logger("app.users")

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

admin_router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
    dependencies=[Depends(require_admin)],
)

@router.get("/me")
async def current_user(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(current_user)

@router.patch("/me")
async def update_current_user(
    payload: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    data = payload.model_dump(exclude_unset=True)
    new_email = data.get("email")
    if new_email:
        # case-insensitive lookup for existing email
        stmt = select(User).where(func.lower(User.email) == new_email.lower())
        res = await db.execute(stmt)
        existing = res.scalars().one_or_none()
        if existing and existing.id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already in use",
            )
        current_user.email = new_email
        current_user.is_verified = False
        
    if "password" in data:
        current_user.hashed_password = hash_password(data.pop("password"))
        
    allowed_fields = {"username", "email", "first_name", "last_name", "phone_number", "date_of_birth"}
    for key, value in data.items():
        if key in allowed_fields:
            setattr(current_user, key, value)
            
    db.add(current_user)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error updating user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict updating user",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        ) from e

    await db.refresh(current_user)

    # If email changed, generate verification token and send email (don't fail the request on send error)
    if new_email:
        token = generate_verification_token()
        expiry = create_verification_token_expiry()
        current_user.verification_token = token
        current_user.verification_token_expiry = expiry
        db.add(current_user)
        try:
            await db.commit()
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to commit verification token for user {current_user.id}: {e}")
        try:
            await send_verification_email(current_user.email, token)
        except Exception as e:
            logger.error(f"Failed to send verification email to {current_user.email}: {e}")

    return UserResponse.model_validate(current_user)
    
    
@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    try:
        await db.delete(current_user)
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        ) from e