from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.user import UserCreate, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)

    async def get_user(self, user_id: int) -> User:
        user = await self.user_repository.get_by_id(user_id)

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    async def get_user_by_email(self, email: str) -> User | None:
        return await self.user_repository.get_by_email(email)

    async def create_user(self, data: UserCreate) -> User:
        if await self.user_repository.email_exists(data.email):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already exists",
            )

        # TODO: Ngay 4 thay bang password hashing that.
        user = await self.user_repository.create(
            {
                "email": str(data.email),
                "hashed_password": data.password,
                "full_name": data.full_name,
            }
        )

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def update_user(self, user: User, data: UserUpdate) -> User:
        update_data = data.model_dump(exclude_unset=True)

        new_email = update_data.get("email")
        if new_email is not None and new_email != user.email:
            if await self.user_repository.email_exists(str(new_email)):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Email already exists",
                )

            update_data["email"] = str(new_email)

        updated_user = await self.user_repository.update(user, update_data)

        await self.session.commit()
        await self.session.refresh(updated_user)
        return updated_user

    async def list_users(self, page: int, limit: int) -> tuple[list[User], int]:
        return await self.user_repository.paginate(page=page, limit=limit)
