from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.responses import COMMON_ERROR_RESPONSES
from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.label import Label
from app.models.user import User
from app.schemas.label import LabelCreate, LabelResponse, LabelUpdate, TaskLabelRequest
from app.services.label import LabelService

router = APIRouter(tags=["Labels"], responses=COMMON_ERROR_RESPONSES)


@router.post(
    "/workspaces/{workspace_id}/projects/{project_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create label",
    description="Create a label in a project. Owner or editor role is required.",
)
async def create_label(
    workspace_id: int,
    project_id: int,
    data: LabelCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Label:
    service = LabelService(session)
    return await service.create_label(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        data=data,
    )


@router.get(
    "/workspaces/{workspace_id}/projects/{project_id}/labels",
    response_model=list[LabelResponse],
    summary="List labels",
    description="List labels in a project.",
)
async def list_labels(
    workspace_id: int,
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> list[Label]:
    service = LabelService(session)
    return await service.list_labels(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
    )


@router.get(
    "/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
    response_model=LabelResponse,
)
async def get_label(
    workspace_id: int,
    project_id: int,
    label_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Label:
    service = LabelService(session)
    return await service.get_label(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        label_id=label_id,
    )


@router.patch(
    "/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
    response_model=LabelResponse,
)
async def update_label(
    workspace_id: int,
    project_id: int,
    label_id: int,
    data: LabelUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Label:
    service = LabelService(session)
    return await service.update_label(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        label_id=label_id,
        data=data,
    )


@router.delete(
    "/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_label(
    workspace_id: int,
    project_id: int,
    label_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service = LabelService(session)
    await service.delete_label(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        label_id=label_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/labels",
    response_model=LabelResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Attach label to task",
    description="Attach a project label to a task in the same project.",
)
async def attach_label_to_task(
    workspace_id: int,
    project_id: int,
    task_id: int,
    data: TaskLabelRequest,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Label:
    service = LabelService(session)
    return await service.attach_label(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        label_id=data.label_id,
    )


@router.delete(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/labels/{label_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def detach_label_from_task(
    workspace_id: int,
    project_id: int,
    task_id: int,
    label_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service = LabelService(session)
    await service.detach_label(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        label_id=label_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
