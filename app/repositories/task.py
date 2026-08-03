from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.repositories.base import BaseRepository


def _task_filters(
    project_id: int,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
) -> list[ColumnElement[bool]]:
    filters: list[ColumnElement[bool]] = [Task.project_id == project_id]

    if status is not None:
        filters.append(Task.status == status)

    if priority is not None:
        filters.append(Task.priority == priority)

    if assignee_id is not None:
        filters.append(Task.assignee_id == assignee_id)

    return filters


class TaskRepository(BaseRepository[Task]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Task)

    async def list_by_project(
        self,
        project_id: int,
        offset: int,
        limit: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
    ) -> list[Task]:
        filters = _task_filters(
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )

        result = await self.session.execute(
            select(Task)
            .where(*filters)
            .order_by(Task.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_project(
        self,
        project_id: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
    ) -> int:
        filters = _task_filters(
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )

        result = await self.session.execute(
            select(func.count()).select_from(Task).where(*filters)
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
