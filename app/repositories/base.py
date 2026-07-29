import builtins
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base


class BaseRepository[T: Base]:
    def __init__(self, session: AsyncSession, model: type[T]) -> None:
        self.session = session
        self.model = model

    async def get_by_id(self, obj_id: int) -> T | None:
        return await self.session.get(self.model, obj_id)

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 20,
    ) -> list[T]:
        statement = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(statement)
        return list(result.scalars().all())

    async def count(self) -> int:
        statement = select(func.count()).select_from(self.model)
        result = await self.session.execute(statement)
        return result.scalar_one()

    async def paginate(
        self,
        *,
        page: int = 1,
        limit: int = 20,
    ) -> tuple[builtins.list[T], int]:
        offset = (page - 1) * limit
        items = await self.list(offset=offset, limit=limit)
        total = await self.count()
        return items, total

    async def create(self, data: dict[str, Any]) -> T:
        obj = self.model(**data)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: T, data: dict[str, Any]) -> T:
        for field, value in data.items():
            setattr(obj, field, value)

        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def delete(self, obj: T) -> None:
        await self.session.delete(obj)
        await self.session.flush()
