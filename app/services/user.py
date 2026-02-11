from typing import Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logs.logging_utils import get_logger
from app.core.security import hash_password
from app.models.user import User
from app.schemas.user import UserUpdate
from app.util.email import (
    create_verification_token_expiry,
    generate_verification_token,
    send_verification_email,
)

logger = get_logger("app.users")


class UserService:
    """Business logic for user management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        """Get a user by ID."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalars().unique().first()

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get a user by email (case-insensitive)."""
        stmt = select(User).where(func.lower(User.email) == email.lower())
        res = await self.db.execute(stmt)
        return res.scalars().one_or_none()

    async def update_current_user(self, current_user: User, payload: UserUpdate) -> User:
        data = payload.model_dump(exclude_unset=True)
        new_email = data.get("email")
        token = None
        if new_email:
            stmt = select(User).where(func.lower(User.email) == new_email.lower())
            res = await self.db.execute(stmt)
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

        allowed_fields = {
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(current_user, key, value)

        self.db.add(current_user)
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error updating user {current_user.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict updating user",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user {current_user.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            ) from e

        await self.db.refresh(current_user)

        if new_email and token:
            try:
                await send_verification_email(current_user.email, token)
            except Exception as e:
                logger.error(
                    f"Failed to send verification email to {current_user.email}: {e}"
                )

        return current_user

    async def delete_current_user(self, current_user: User) -> None:
        try:
            await self.db.delete(current_user)
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error deleting user {current_user.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict deleting user",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete user {current_user.id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user",
            ) from e

    async def list_users(self) -> list[User]:
        stmt = select(User)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_user_stats(self) -> dict[str, int]:
        total_users_stmt = select(func.count(User.id))
        result = await self.db.execute(total_users_stmt)
        total_users = result.scalar_one()

        verified_users_stmt = select(func.count(User.id)).where(User.is_verified)
        result = await self.db.execute(verified_users_stmt)
        verified_users = result.scalar_one()

        admin_users_stmt = select(func.count(User.id)).where(User.is_admin)
        result = await self.db.execute(admin_users_stmt)
        admin_users = result.scalar_one()

        active_users_stmt = select(func.count(User.id)).where(User.is_active)
        result = await self.db.execute(active_users_stmt)
        active_users = result.scalar_one()

        return {
            "total_users": total_users,
            "verified_users": verified_users,
            "admin_users": admin_users,
            "active_users": active_users,
        }

    async def get_user(self, user_id: UUID) -> User:
        user = await self.db.get(User, user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        return user

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.get_user(user_id)
        try:
            await self.db.delete(user)
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error deleting user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict deleting user",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to delete user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete user",
            ) from e

    async def update_user(self, user_id: UUID, payload: UserUpdate) -> User:
        user = await self.get_user(user_id)
        data = payload.model_dump(exclude_unset=True)
        if "password" in data:
            user.hashed_password = hash_password(data.pop("password"))
        allowed_fields = {
            "username",
            "email",
            "first_name",
            "last_name",
            "phone_number",
            "date_of_birth",
        }
        for key, value in data.items():
            if key in allowed_fields:
                setattr(user, key, value)
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError as e:
            await self.db.rollback()
            logger.error(f"Integrity error updating user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict updating user",
            ) from e
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to update user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            ) from e
        await self.db.refresh(user)
        return user

    async def make_admin(self, user_id: UUID) -> User:
        user = await self.get_user(user_id)
        if user.is_admin:
            logger.info(f"User {user_id} is already an admin")
            return user

        user.is_admin = True
        self.db.add(user)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to make user {user_id} admin: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            ) from e
        await self.db.refresh(user)
        return user

    async def revoke_admin(self, user_id: UUID) -> User:
        user = await self.get_user(user_id)
        if not user.is_admin:
            logger.info(f"User {user_id} is not an admin")
            return user

        user.is_admin = False
        self.db.add(user)
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to revoke admin from user {user_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user",
            ) from e
        await self.db.refresh(user)
        return user
