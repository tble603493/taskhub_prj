from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate
from app.services.user import UserService

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user_stub(session: DbSession) -> User:
    # Dependency tam cho Ngay 3. Ngay 4 se thay bang JWT get_current_user.
    statement = select(User).order_by(User.id).limit(1)

    result = await session.execute(statement)
    user = result.scalar_one_or_none()

    if user is not None:
        return user

    user_service = UserService(session)

    return await user_service.create_user(
        UserCreate(
            email="dev@example.com",
            password="dev_password_123",
            full_name="Dev User",
        )
    )
