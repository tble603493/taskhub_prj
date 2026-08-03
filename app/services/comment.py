from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.permissions import can_delete_comment
from app.models.comment import Comment
from app.models.enums import ProjectStatus
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace_member import WorkspaceMember
from app.repositories.comment import CommentRepository
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace_member import WorkspaceMemberRepository
from app.schemas.comment import CommentCreate


def _ensure_project_active(project: Project) -> None:
    if project.status == ProjectStatus.ARCHIVED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project is archived",
        )


class CommentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.comment_repo = CommentRepository(session)
        self.project_repo = ProjectRepository(session)
        self.task_repo = TaskRepository(session)
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

    async def _get_comment_in_task(
        self,
        task_id: int,
        comment_id: int,
    ) -> Comment:
        comment = await self.comment_repo.get_by_task(
            comment_id=comment_id,
            task_id=task_id,
        )
        if comment is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Comment not found",
            )
        return comment

    async def create_comment(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
        data: CommentCreate,
    ) -> Comment:
        await self._get_membership(current_user, workspace_id)

        project = await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        _ensure_project_active(project)

        await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        comment = await self.comment_repo.create(
            {
                "task_id": task_id,
                "author_id": current_user.id,
                "content": data.content,
            }
        )

        await self.session.commit()
        await self.session.refresh(comment)

        return comment

    async def list_comments(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
    ) -> list[Comment]:
        await self._get_membership(current_user, workspace_id)

        await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        return await self.comment_repo.list_by_task(task_id)

    async def delete_comment(
        self,
        current_user: User,
        workspace_id: int,
        project_id: int,
        task_id: int,
        comment_id: int,
    ) -> None:
        member = await self._get_membership(current_user, workspace_id)

        await self._get_project_in_workspace(
            workspace_id=workspace_id,
            project_id=project_id,
        )

        await self._get_task_in_project(
            project_id=project_id,
            task_id=task_id,
        )

        comment = await self._get_comment_in_task(
            task_id=task_id,
            comment_id=comment_id,
        )

        if not can_delete_comment(
            current_user=current_user,
            member=member,
            comment=comment,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions to delete this comment",
            )

        await self.comment_repo.delete(comment)
        await self.session.commit()
