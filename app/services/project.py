from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus, WorkspaceRole
from app.models.project import Project
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.project import ProjectRepository
from app.repositories.workspace_member import WorkspaceMemberRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate

WRITE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.EDITOR}


def _require_project_write(member: WorkspaceMember) -> None:
    if member.role not in WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions for this project",
        )


def _ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is archived",
        )


class ProjectService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.project_repo = ProjectRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)

    async def _get_membership(
        self,
        current_user: User,
        workspace_id: int,
    ) -> WorkspaceMember:
        member = await self.member_repo.get_by_workspace_and_user(
            workspace_id=workspace_id,
            user_id=current_user.id,
        )
        if member is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You are not a member of this workspace",
            )
        return member

    async def _get_project_in_workspace(
        self,
        workspace_id: int,
        project_id: int,
    ) -> Project:
        project = await self.project_repo.get_by_workspace(
            project_id=project_id,
            workspace_id=workspace_id,
        )
        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )
        return project

    async def create_project(
        self,
        current_user: User,
        workspace_id: int,
        data: ProjectCreate,
    ) -> Project:
        member = await self._get_membership(current_user, workspace_id)
        _require_project_write(member)

        existing_project = await self.project_repo.get_by_workspace_and_name(
            workspace_id=workspace_id,
            name=data.name,
        )
        if existing_project is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Project name already exists in this workspace",
            )

        project = await self.project_repo.create(
            {
                "workspace_id": workspace_id,
                "name": data.name,
                "description": data.description,
                "status": ProjectStatus.ACTIVE,
            }
        )
        await self.session.commit()
        await self.session.refresh(project)
        return project

    async def list_projects(
        self,
        current_user: User,
        workspace_id: int,
        page: int,
        limit: int,
    ) -> PaginatedResponse[ProjectResponse]:
        await self._get_membership(current_user, workspace_id)

        offset = (page - 1) * limit
        projects = await self.project_repo.list_by_workspace(
            workspace_id=workspace_id,
            offset=offset,
            limit=limit,
        )
        total = await self.project_repo.count_by_workspace(workspace_id)
        pages = (total + limit - 1) // limit if total > 0 else 0

        return PaginatedResponse[ProjectResponse](
            items=[
                ProjectResponse.model_validate(project)
                for project in projects
            ],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_project(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
    ) -> Project:
        await self._get_membership(current_user, workspace_id)
        return await self._get_project_in_workspace(workspace_id, project_id)

    async def update_project(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        data: ProjectUpdate,
    ) -> Project:
        member = await self._get_membership(current_user, workspace_id)
        _require_project_write(member)

        project = await self._get_project_in_workspace(workspace_id, project_id)
        _ensure_project_active(project)

        update_data = data.model_dump(exclude_unset=True)

        new_name = update_data.get("name")
        if new_name and new_name != project.name:
            existing_project = await self.project_repo.get_by_workspace_and_name(
                workspace_id=workspace_id,
                name=new_name,
            )
            if existing_project is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Project name already exists in this workspace",
                )

        updated_project = await self.project_repo.update(project, update_data)
        await self.session.commit()
        await self.session.refresh(updated_project)
        return updated_project

    async def archive_project(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
    ) -> Project:
        member = await self._get_membership(current_user, workspace_id)
        _require_project_write(member)

        project = await self._get_project_in_workspace(workspace_id, project_id)

        archived_project = await self.project_repo.update(
            project,
            {"status": ProjectStatus.ARCHIVED},
        )
        await self.session.commit()
        await self.session.refresh(archived_project)
        return archived_project

    async def delete_project(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
    ) -> None:
        member = await self._get_membership(current_user, workspace_id)

        if member.role != WorkspaceRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only workspace owner can delete project",
            )

        project = await self._get_project_in_workspace(workspace_id, project_id)
        await self.project_repo.delete(project)
        await self.session.commit()
