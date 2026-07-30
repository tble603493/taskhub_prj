from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceRepository(BaseRepository[Workspace]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, Workspace)

    async def list_by_user(
        self,
        *,
        user_id: int,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Workspace]:
        statement = (
            select(Workspace)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
            .offset(offset)
            .limit(limit)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def count_by_user(self, user_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(Workspace)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(WorkspaceMember.user_id == user_id)
        )

        result = await self.session.execute(statement)

        return result.scalar_one()

    async def get_with_membership(
        self,
        *,
        workspace_id: int,
        user_id: int,
    ) -> Workspace | None:
        statement = (
            select(Workspace)
            .join(
                WorkspaceMember,
                WorkspaceMember.workspace_id == Workspace.id,
            )
            .where(
                Workspace.id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()
