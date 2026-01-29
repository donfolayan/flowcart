from fastapi import APIRouter, Depends, HTTPException, status
from uuid import UUID
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
    token = None
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
        token = generate_verification_token()
        expiry = create_verification_token_expiry()
        current_user.email = new_email
        current_user.is_verified = False
        current_user.verification_token = token
        current_user.verification_token_expiry = expiry
        
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

    if new_email and token:
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
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error deleting user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict deleting user",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user {current_user.id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        ) from e
        
@admin_router.get("/")
async def list_users(
    db: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    stmt = select(User)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [UserResponse.model_validate(user) for user in users]

@admin_router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    return UserResponse.model_validate(user)

@admin_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    try:
        await db.delete(user)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error deleting user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict deleting user",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to delete user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        ) from e
        
@admin_router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    data = payload.model_dump(exclude_unset=True)
    if "password" in data:
        user.hashed_password = hash_password(data.pop("password"))
    allowed_fields = {"username", "email", "first_name", "last_name", "phone_number", "date_of_birth"}
    for key, value in data.items():
        if key in allowed_fields:
            setattr(user, key, value)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"Integrity error updating user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict updating user",
        ) from e
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to update user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        ) from e
    await db.refresh(user)
    return UserResponse.model_validate(user)

@admin_router.post("/make-admin")
async def make_user_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if user.is_admin:
        logger.info(f"User {user_id} is already an admin")
        return UserResponse.model_validate(user)
    
    user.is_admin = True
    db.add(user)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to make user {user_id} admin: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        ) from e
    await db.refresh(user)
    return UserResponse.model_validate(user)

@admin_router.post("/revoke-admin")
async def revoke_user_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )
    if not user.is_admin:
        logger.info(f"User {user_id} is not an admin")
        return UserResponse.model_validate(user)
    
    user.is_admin = False
    db.add(user)
    try:
        await db.commit()
    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to revoke admin from user {user_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        ) from e
    await db.refresh(user)
    return UserResponse.model_validate(user)