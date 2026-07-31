from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project
from app.repositories.base import BaseRepository


class ProjectRepository(BaseRepository[Project]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session=session, model=Project)

    async def list_by_workspace(
        self,
        workspace_id: int,
        offset: int,
        limit: int,
    ) -> list[Project]:
        result = await self.session.execute(
            select(Project)
            .where(Project.workspace_id == workspace_id)
            .order_by(Project.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_by_workspace(self, workspace_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(Project)
            .where(Project.workspace_id == workspace_id)
        )
        return result.scalar_one()

    async def get_by_workspace(
        self,
        project_id: int,
        workspace_id: int,
    ) -> Project | None:
        result = await self.session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_workspace_and_name(
        self,
        workspace_id: int,
        name: str,
    ) -> Project | None:
        result = await self.session.execute(
            select(Project).where(
                Project.workspace_id == workspace_id,
                Project.name == name,
            )
        )
        return result.scalar_one_or_none()