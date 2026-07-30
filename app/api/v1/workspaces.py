from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_active_user
from app.db.session import get_db
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.schemas.pagination import PaginatedResponse
from app.schemas.workspace import (
    WorkspaceCreate,
    WorkspaceMemberCreate,
    WorkspaceMemberResponse,
    WorkspaceMemberUpdate,
    WorkspaceMemberWithUserResponse,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from app.services.workspace import WorkspaceService

router = APIRouter(tags=["Workspaces"])

DbSession = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_active_user)]


@router.post(
    "",
    response_model=WorkspaceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_workspace(
    data: WorkspaceCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    workspace_service = WorkspaceService(session)

    return await workspace_service.create_workspace(current_user, data)


@router.get(
    "",
    response_model=PaginatedResponse[WorkspaceResponse],
)
async def list_workspaces(
    current_user: CurrentUser,
    session: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[WorkspaceResponse]:
    workspace_service = WorkspaceService(session)

    workspaces, total = await workspace_service.list_workspaces(
        current_user=current_user,
        page=page,
        limit=limit,
    )

    pages = 0 if total == 0 else (total + limit - 1) // limit

    return PaginatedResponse[WorkspaceResponse](
        items=[WorkspaceResponse.model_validate(workspace) for workspace in workspaces],
        total=total,
        page=page,
        limit=limit,
        pages=pages,
    )


@router.get(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def get_workspace(
    workspace_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    workspace_service = WorkspaceService(session)

    return await workspace_service.get_workspace(current_user, workspace_id)


@router.patch(
    "/{workspace_id}",
    response_model=WorkspaceResponse,
)
async def update_workspace(
    workspace_id: int,
    data: WorkspaceUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> Workspace:
    workspace_service = WorkspaceService(session)

    return await workspace_service.update_workspace(
        current_user=current_user,
        workspace_id=workspace_id,
        data=data,
    )


@router.delete(
    "/{workspace_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_workspace(
    workspace_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    workspace_service = WorkspaceService(session)

    await workspace_service.delete_workspace(
        current_user=current_user,
        workspace_id=workspace_id,
    )


@router.post(
    "/{workspace_id}/members",
    response_model=WorkspaceMemberResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_member(
    workspace_id: int,
    data: WorkspaceMemberCreate,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceMember:
    workspace_service = WorkspaceService(session)

    return await workspace_service.add_member(
        current_user=current_user,
        workspace_id=workspace_id,
        data=data,
    )


@router.get(
    "/{workspace_id}/members",
    response_model=list[WorkspaceMemberWithUserResponse],
)
async def list_members(
    workspace_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> list[WorkspaceMember]:
    workspace_service = WorkspaceService(session)

    return await workspace_service.list_members(
        current_user=current_user,
        workspace_id=workspace_id,
    )


@router.patch(
    "/{workspace_id}/members/{member_id}",
    response_model=WorkspaceMemberResponse,
)
async def update_member(
    workspace_id: int,
    member_id: int,
    data: WorkspaceMemberUpdate,
    current_user: CurrentUser,
    session: DbSession,
) -> WorkspaceMember:
    workspace_service = WorkspaceService(session)

    return await workspace_service.update_member(
        current_user=current_user,
        workspace_id=workspace_id,
        member_id=member_id,
        data=data,
    )


@router.delete(
    "/{workspace_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_member(
    workspace_id: int,
    member_id: int,
    current_user: CurrentUser,
    session: DbSession,
) -> None:
    workspace_service = WorkspaceService(session)

    await workspace_service.remove_member(
        current_user=current_user,
        workspace_id=workspace_id,
        member_id=member_id,
    )
