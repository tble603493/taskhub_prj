from sqlalchemy import delete, exists, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.label import Label
from app.models.task_label import TaskLabel
from app.repositories.base import BaseRepository


class LabelRepository(BaseRepository[Label]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Label)

    async def list_by_project(
        self,
        project_id: int,
    ) -> list[Label]:
        result = await self.session.execute(
            select(Label).where(Label.project_id == project_id).order_by(Label.name)
        )
        return list(result.scalars().all())

    async def get_by_project(
        self,
        label_id: int,
        project_id: int,
    ) -> Label | None:
        result = await self.session.execute(
            select(Label).where(
                Label.id == label_id,
                Label.project_id == project_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_project_and_name(
        self,
        project_id: int,
        name: str,
    ) -> Label | None:
        result = await self.session.execute(
            select(Label).where(
                Label.project_id == project_id,
                Label.name == name,
            )
        )
        return result.scalar_one_or_none()

    async def is_attached_to_task(
        self,
        task_id: int,
        label_id: int,
    ) -> bool:
        result = await self.session.execute(
            select(
                exists().where(
                    TaskLabel.task_id == task_id,
                    TaskLabel.label_id == label_id,
                )
            )
        )
        return bool(result.scalar())

    async def attach_to_task(
        self,
        task_id: int,
        label_id: int,
    ) -> None:
        if await self.is_attached_to_task(task_id, label_id):
            return

        await self.session.execute(
            insert(TaskLabel).values(
                task_id=task_id,
                label_id=label_id,
            )
        )

    async def detach_from_task(
        self,
        task_id: int,
        label_id: int,
    ) -> None:
        await self.session.execute(
            delete(TaskLabel).where(
                TaskLabel.task_id == task_id,
                TaskLabel.label_id == label_id,
            )
        )
