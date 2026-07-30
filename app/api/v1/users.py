from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest
from app.schemas.pagination import PaginatedResponse
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.user import UserService

router = APIRouter(tags=["Users"])


DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_me(current_user: CurrentUser) -> User:
    return current_user


@router.patch(
    "/me",
    response_model=UserResponse,
)
async def update_me(
    data: UserUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> User:
    user_service = UserService(session)

    return await user_service.update_user(current_user, data)


@router.patch(
    "/me/password",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def change_my_password(
    data: ChangePasswordRequest,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    user_service = UserService(session)

    await user_service.change_password(current_user, data)


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    data: UserCreate,
    session: DbSession,
) -> User:
    user_service = UserService(session)

    return await user_service.create_user(data)


@router.get(
    "",
    response_model=PaginatedResponse[UserResponse],
)
async def list_users(
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[UserResponse]:
    user_service = UserService(session)

    users, total = await user_service.list_users(page=page, limit=limit)
    pages = 0 if total == 0 else (total + limit - 1) // limit

    return PaginatedResponse[UserResponse](
        items=[UserResponse.model_validate(user) for user in users],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    session: DbSession,
) -> User:
    user_service = UserService(session)

    return await user_service.get_user(user_id)
