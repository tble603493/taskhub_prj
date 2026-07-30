from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.user import UserRepository
from app.repositories.workspace import WorkspaceRepository
from app.repositories.workspace_member import WorkspaceMemberRepository
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberUpdate,
    WorkspaceUpdate,
)


class WorkspaceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.workspace_repository = WorkspaceRepository(session)
        self.member_repository = WorkspaceMemberRepository(session)
        self.user_repository = UserRepository(session)

    async def create_workspace(
        self,
        current_user: User,
        data: WorkspaceCreate,
    ) -> Workspace:
        workspace = await self.workspace_repository.create(
            {
                "name": data.name,
                "description": data.description,
            }
        )

        await self.member_repository.create(
            {
                "workspace_id": workspace.id,
                "user_id": current_user.id,
                "role": WorkspaceRole.OWNER,
            }
        )

        await self.session.commit()
        await self.session.refresh(workspace)

        return workspace

    async def list_workspaces(
        self,
        current_user: User,
        page: int,
        limit: int,
    ) -> tuple[list[Workspace], int]:
        offset = (page - 1) * limit

        items = await self.workspace_repository.list_by_user(
            user_id=current_user.id,
            offset=offset,
            limit=limit,
        )

        total = await self.workspace_repository.count_by_user(current_user.id)

        return items, total

    async def get_workspace(
        self,
        current_user: User,
        workspace_id: int,
    ) -> Workspace:
        workspace = await self.workspace_repository.get_with_membership(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        if workspace is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        return workspace

    async def update_workspace(
        self,
        current_user: User,
        workspace_id: int,
        data: WorkspaceUpdate,
    ) -> Workspace:
        workspace = await self.get_workspace(current_user, workspace_id)

        await self._require_owner(current_user, workspace_id)

        update_data = data.model_dump(exclude_unset=True)

        updated_workspace = await self.workspace_repository.update(
            workspace,
            update_data,
        )

        await self.session.commit()
        await self.session.refresh(updated_workspace)

        return updated_workspace

    async def delete_workspace(
        self,
        current_user: User,
        workspace_id: int,
    ) -> None:
        workspace = await self.get_workspace(current_user, workspace_id)

        await self._require_owner(current_user, workspace_id)

        await self.workspace_repository.delete(workspace)
        await self.session.commit()

    async def add_member(
        self,
        current_user: User,
        workspace_id: int,
        data: WorkspaceMemberCreate,
    ) -> WorkspaceMember:
        await self.get_workspace(current_user, workspace_id)
        await self._require_owner(current_user, workspace_id)

        user = await self.user_repository.get_by_email(str(data.email))

        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if await self.member_repository.exists(
            workspace_id=workspace_id,
            user_id=user.id,
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User is already a workspace member",
            )

        member = await self.member_repository.create(
            {
                "workspace_id": workspace_id,
                "user_id": user.id,
                "role": data.role,
            }
        )

        await self.session.commit()
        await self.session.refresh(member)

        return member

    async def list_members(
        self,
        current_user: User,
        workspace_id: int,
    ) -> list[WorkspaceMember]:
        await self.get_workspace(current_user, workspace_id)

        return await self.member_repository.list_by_workspace(workspace_id)

    async def update_member(
        self,
        current_user: User,
        workspace_id: int,
        member_id: int,
        data: WorkspaceMemberUpdate,
    ) -> WorkspaceMember:
        await self.get_workspace(current_user, workspace_id)
        await self._require_owner(current_user, workspace_id)

        member = await self._get_member_in_workspace(workspace_id, member_id)

        if member.role == WorkspaceRole.OWNER and data.role != WorkspaceRole.OWNER:
            await self._ensure_not_last_owner(workspace_id)

        updated_member = await self.member_repository.update(
            member,
            {
                "role": data.role,
            },
        )

        await self.session.commit()
        await self.session.refresh(updated_member)

        return updated_member

    async def remove_member(
        self,
        current_user: User,
        workspace_id: int,
        member_id: int,
    ) -> None:
        await self.get_workspace(current_user, workspace_id)
        await self._require_owner(current_user, workspace_id)

        member = await self._get_member_in_workspace(workspace_id, member_id)

        if member.role == WorkspaceRole.OWNER:
            await self._ensure_not_last_owner(workspace_id)

        await self.member_repository.delete(member)
        await self.session.commit()

    async def _require_owner(
        self,
        current_user: User,
        workspace_id: int,
    ) -> WorkspaceMember:
        member = await self.member_repository.get_by_workspace_and_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )

        if member is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace not found",
            )

        if member.role != WorkspaceRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owners can perform this action",
            )

        return member

    async def _get_member_in_workspace(
        self,
        workspace_id: int,
        member_id: int,
    ) -> WorkspaceMember:
        member = await self.member_repository.get_by_id(member_id)

        if member is None or member.workspace_id != workspace_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workspace member not found",
            )

        return member

    async def _ensure_not_last_owner(self, workspace_id: int) -> None:
        owner_count = await self.member_repository.count_owners(workspace_id)

        if owner_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot remove or demote the last workspace owner",
            )
