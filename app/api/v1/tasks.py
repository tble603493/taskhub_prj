from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.enums import TaskPriority, TaskStatus
from app.models.task import Task
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate
from app.services.notification import notify_task_assigned_safely
from app.services.task import TaskService

router = APIRouter(tags=["tasks"])


@router.post(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    workspace_id: int,
    project_id: int,
    data: TaskCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Task:
    service = TaskService(session)
    return await service.create_task(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        data=data,
    )


@router.get(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks",
    response_model=PaginatedResponse[TaskResponse],
)
async def list_tasks(
    workspace_id: int,
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
) -> PaginatedResponse[TaskResponse]:
    service = TaskService(session)
    return await service.list_tasks(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        page=page,
        limit=limit,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
    )


@router.get(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    workspace_id: int,
    project_id: int,
    task_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Task:
    service = TaskService(session)
    return await service.get_task(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
    )


@router.patch(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    workspace_id: int,
    project_id: int,
    task_id: int,
    data: TaskUpdate,
    background_tasks: BackgroundTasks,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Task:
    service = TaskService(session)
    task = await service.update_task(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
        data=data,
    )

    if data.assignee_id is not None:
        background_tasks.add_task(
            notify_task_assigned_safely,
            task_id=task.id,
            assignee_id=data.assignee_id,
        )

    return task


@router.delete(
    "/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    workspace_id: int,
    project_id: int,
    task_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service = TaskService(session)
    await service.delete_task(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        task_id=task_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
