from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import ProjectStatus, TaskPriority, TaskStatus, WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace_member import WorkspaceMemberRepository
from app.schemas.pagination import PaginatedResponse
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

TASK_WRITE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.EDITOR}


def _require_task_write(member: WorkspaceMember) -> None:
    if member.role not in TASK_WRITE_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions for this task",
        )


def _ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is archived",
        )


class TaskService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.task_repo = TaskRepository(session)
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

    async def _get_task_in_project(
        self,
        project_id: int,
        task_id: int,
    ) -> Task:
        task = await self.task_repo.get_by_project(
            task_id=task_id,
            project_id=project_id,
        )
        if task is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found",
            )
        return task

    async def _ensure_assignee_is_workspace_member(
        self,
        workspace_id: int,
        assignee_id: int | None,
    ) -> None:
        if assignee_id is None:
            return

        exists = await self.member_repo.exists(
            workspace_id=workspace_id,
            user_id=assignee_id,
        )
        if not exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignee must be a member of this workspace",
            )

    async def create_task(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        data: TaskCreate,
    ) -> Task:
        member = await self._get_membership(current_user, workspace_id)
        _require_task_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        await self._ensure_assignee_is_workspace_member(
            workspace_id=workspace_id,
            assignee_id=data.assignee_id,
        )

        task = await self.task_repo.create(
            {
                "project_id": project_id,
                "title": data.title,
                "description": data.description,
                "priority": data.priority,
                "due_date": data.due_date,
                "assignee_id": data.assignee_id,
                "created_by_id": current_user.id,
            }
        )

        await self.session.commit()
        await self.session.refresh(task)

        return task

    async def list_tasks(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        page: int,
        limit: int,
        status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        assignee_id: int | None = None,
    ) -> PaginatedResponse[TaskResponse]:
        await self._get_membership(current_user, workspace_id)

        await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        offset = (page - 1) * limit

        tasks = await self.task_repo.list_by_project(
            project_id=project_id,
            offset=offset,
            limit=limit,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )

        total = await self.task_repo.count_by_project(
            project_id=project_id,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )

        pages = (total + limit - 1) // limit if total > 0 else 0

        return PaginatedResponse[TaskResponse](
            items=[TaskResponse.model_validate(task) for task in tasks],
            total=total,
            page=page,
            limit=limit,
            pages=pages,
        )

    async def get_task(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
    ) -> Task:
        await self._get_membership(current_user, workspace_id)

        await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        return await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

    async def update_task(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
        data: TaskUpdate,
    ) -> Task:
        member = await self._get_membership(current_user, workspace_id)
        _require_task_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        task = await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        update_data = data.model_dump(exclude_unset=True)

        if "assignee_id" in update_data:
            await self._ensure_assignee_is_workspace_member(
                workspace_id=workspace_id,
                assignee_id=update_data["assignee_id"],
            )

        updated_task = await self.task_repo.update(task, update_data)

        await self.session.commit()
        await self.session.refresh(updated_task)

        return updated_task

    async def delete_task(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
    ) -> None:
        member = await self._get_membership(current_user, workspace_id)
        _require_task_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        task = await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        await self.task_repo.delete(task)
        await self.session.commit()
