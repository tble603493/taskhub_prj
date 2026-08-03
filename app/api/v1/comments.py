from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.comment import Comment
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentResponse
from app.services.comment import CommentService

router = APIRouter(tags=["comments"])


@router.post(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
    response_model=CommentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_comment(
    workspace_id: int,
    project_id: int,
    task_id: int,
    data: CommentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Comment:
    service = CommentService(session)
    return await service.create_comment(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        data=data,
    )


@router.get(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
    response_model=list[CommentResponse],
)
async def list_comments(
    workspace_id: int,
    project_id: int,
    task_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[Comment]:
    service = CommentService(session)
    return await service.list_comments(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
    )


@router.delete(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_comment(
    workspace_id: int,
    project_id: int,
    task_id: int,
    comment_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service = CommentService(session)
    await service.delete_comment(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        comment_id=comment_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
