from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.pagination import PaginatedResponse
from app.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from app.services.project import ProjectService

router = APIRouter(tags=["projects"])


@router.post(
    "/workspaces/{workspace_id}/projects",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    workspace_id: int,
    data: ProjectCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    service = ProjectService(session)
    return await service.create_project(
        current_user=current_user,
        workspace_id=workspace_id,
        data=data,
    )


@router.get(
    "/workspaces/{workspace_id}/projects",
    response_model=PaginatedResponse[ProjectResponse],
)
async def list_projects(
    workspace_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[ProjectResponse]:
    service = ProjectService(session)
    return await service.list_projects(
        current_user=current_user,
        workspace_id=workspace_id,
        page=page,
        limit=limit,
    )


@router.get(
    "/workspaces/{workspace_id}/projects/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(
    workspace_id: int,
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    service = ProjectService(session)
    return await service.get_project(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
    )


@router.patch(
    "/workspaces/{workspace_id}/projects/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    workspace_id: int,
    project_id: int,
    data: ProjectUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    service = ProjectService(session)
    return await service.update_project(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
        data=data,
    )


@router.patch(
    "/workspaces/{workspace_id}/projects/{project_id}/archive",
    response_model=ProjectResponse,
)
async def archive_project(
    workspace_id: int,
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Project:
    service = ProjectService(session)
    return await service.archive_project(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
    )


@router.delete(
    "/workspaces/{workspace_id}/projects/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    workspace_id: int,
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> Response:
    service = ProjectService(session)
    await service.delete_project(
        current_user=current_user,
        workspace_id=workspace_id,
        project_id=project_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
