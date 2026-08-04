from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import require_content_write
from app.models.enums import ProjectStatus
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.label import LabelRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace_member import WorkspaceMemberRepository
from app.schemas.label import LabelCreate, LabelUpdate
from app.services.cache import CacheService
from app.services.task_cache import invalidate_task_list_cache


def _ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is archived",
        )


class LabelService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.label_repo = LabelRepository(session)
        self.project_repo = ProjectRepository(session)
        self.task_repo = TaskRepository(session)
        self.member_repo = WorkspaceMemberRepository(session)
        self.cache_service = CacheService()

    async def _invalidate_task_list_cache(
        self,
        workspace_id: int,
        project_id: int,
    ) -> None:
        await invalidate_task_list_cache(
            cache_service=self.cache_service,
            workspace_id=workspace_id,
            project_id=project_id,
        )

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

    async def _get_label_in_project(
        self,
        project_id: int,
        label_id: int,
    ) -> Label:
        label = await self.label_repo.get_by_project(
            label_id=label_id,
            project_id=project_id,
        )
        if label is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found",
            )
        return label

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

    async def create_label(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        data: LabelCreate,
    ) -> Label:
        member = await self._get_membership(current_user, workspace_id)
        require_content_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        existing_label = await self.label_repo.get_by_project_and_name(
            project_id=project_id,
            name=data.name,
        )
        if existing_label is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Label name already exists in this project",
            )

        label = await self.label_repo.create(
            {
                "project_id": project_id,
                "name": data.name,
                "color": data.color,
            }
        )

        await self.session.commit()
        await self.session.refresh(label)

        return label

    async def list_labels(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
    ) -> list[Label]:
        await self._get_membership(current_user, workspace_id)
        await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        return await self.label_repo.list_by_project(project_id)

    async def get_label(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        label_id: int,
    ) -> Label:
        await self._get_membership(current_user, workspace_id)
        await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        return await self._get_label_in_project(
            project_id=project_id,
            label_id=label_id,
        )

    async def update_label(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        label_id: int,
        data: LabelUpdate,
    ) -> Label:
        member = await self._get_membership(current_user, workspace_id)
        require_content_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        label = await self._get_label_in_project(
            project_id=project_id,
            label_id=label_id,
        )

        update_data = data.model_dump(exclude_unset=True)

        new_name = update_data.get("name")
        if new_name and new_name != label.name:
            existing_label = await self.label_repo.get_by_project_and_name(
                project_id=project_id,
                name=new_name,
            )
            if existing_label is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Label name already exists in this project",
                )

        updated_label = await self.label_repo.update(label, update_data)

        await self.session.commit()
        await self.session.refresh(updated_label)

        return updated_label

    async def delete_label(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        label_id: int,
    ) -> None:
        member = await self._get_membership(current_user, workspace_id)
        require_content_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        label = await self._get_label_in_project(
            project_id=project_id,
            label_id=label_id,
        )

        await self.label_repo.delete(label)
        await self.session.commit()

    async def attach_label(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
        label_id: int,
    ) -> Label:
        member = await self._get_membership(current_user, workspace_id)
        require_content_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        label = await self._get_label_in_project(
            project_id=project_id,
            label_id=label_id,
        )

        await self.label_repo.attach_to_task(
            task_id=task_id,
            label_id=label_id,
        )

        await self.session.commit()
        await self._invalidate_task_list_cache(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        return label

    async def detach_label(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
        label_id: int,
    ) -> None:
        member = await self._get_membership(current_user, workspace_id)
        require_content_write(member)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        await self._get_label_in_project(
            project_id=project_id,
            label_id=label_id,
        )

        await self.label_repo.detach_from_task(
            task_id=task_id,
            label_id=label_id,
        )

        await self.session.commit()
        await self._invalidate_task_list_cache(
            workspace_id=workspace_id,
            project_id=project_id,
        )
