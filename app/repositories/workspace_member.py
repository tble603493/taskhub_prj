from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import WorkspaceRole
from app.models.workspace_member import WorkspaceMember
from app.repositories.base import BaseRepository


class WorkspaceMemberRepository(BaseRepository[WorkspaceMember]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, WorkspaceMember)

    async def get_by_workspace_and_user(
        self,
        *,
        workspace_id: int,
        user_id: int,
    ) -> WorkspaceMember | None:
        statement = select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace_id,
            WorkspaceMember.user_id == user_id,
        )

        result = await self.session.execute(statement)

        return result.scalar_one_or_none()

    async def list_by_workspace(
        self,
        workspace_id: int,
    ) -> list[WorkspaceMember]:
        statement = (
            select(WorkspaceMember)
            .where(WorkspaceMember.workspace_id == workspace_id)
            .options(selectinload(WorkspaceMember.user))
            .order_by(WorkspaceMember.id)
        )

        result = await self.session.execute(statement)

        return list(result.scalars().all())

    async def count_owners(self, workspace_id: int) -> int:
        statement = (
            select(func.count())
            .select_from(WorkspaceMember)
            .where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.role == WorkspaceRole.OWNER,
            )
        )

        result = await self.session.execute(statement)

        return result.scalar_one()

    async def exists(
        self,
        *,
        workspace_id: int,
        user_id: int,
    ) -> bool:
        member = await self.get_by_workspace_and_user(
            workspace_id=workspace_id,
            user_id=user_id,
        )

        return member is not None
