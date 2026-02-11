from fastapi import APIRouter, Depends, status
from uuid import UUID
from app.core.permissions import require_admin
from app.core.security import get_current_user
from app.db.session import get_session, AsyncSession
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user import UserService


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
    service = UserService(db)
    user = await service.update_current_user(current_user=current_user, payload=payload)
    return UserResponse.model_validate(user)


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
async def delete_current_user(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
) -> None:
    service = UserService(db)
    await service.delete_current_user(current_user=current_user)


@admin_router.get("/")
async def list_users(
    db: AsyncSession = Depends(get_session),
) -> list[UserResponse]:
    service = UserService(db)
    users = await service.list_users()
    return [UserResponse.model_validate(user) for user in users]


@admin_router.get("/stats")
async def get_user_stats(
    db: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    service = UserService(db)
    return await service.get_user_stats()


@admin_router.get("/{user_id}")
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    service = UserService(db)
    user = await service.get_user(user_id=user_id)
    return UserResponse.model_validate(user)


@admin_router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> None:
    service = UserService(db)
    await service.delete_user(user_id=user_id)


@admin_router.patch("/{user_id}")
async def update_user(
    user_id: UUID,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    service = UserService(db)
    user = await service.update_user(user_id=user_id, payload=payload)
    return UserResponse.model_validate(user)


@admin_router.post("/make-admin")
async def make_user_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    service = UserService(db)
    user = await service.make_admin(user_id=user_id)
    return UserResponse.model_validate(user)


@admin_router.post("/revoke-admin")
async def revoke_user_admin(
    user_id: UUID,
    db: AsyncSession = Depends(get_session),
) -> UserResponse:
    service = UserService(db)
    user = await service.revoke_admin(user_id=user_id)
    return UserResponse.model_validate(user)
