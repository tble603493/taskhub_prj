from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task import Task
from app.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Task)

    async def list_by_project(
        self,
        project_id: int,
        offset: int,
        limit: int,
    ) -> list[Task]:
        result = await self.session.execute(
            select(Task)
            .where(Task.project_id == project_id)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_project(self, project_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Task)
            .where(Task.project_id == project_id)
        )
        return result.scalar_one()

    async def get_by_project(
        self,
        task_id: int,
        project_id: int,
    ) -> Task | None:
        result = await self.session.execute(
            select(Task).where(
                Task.id == task_id,
                Task.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()