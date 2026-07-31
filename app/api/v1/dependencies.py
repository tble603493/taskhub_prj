from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token
from app.db.session import get_db
from app.models.enums import WorkspaceRole
from app.models.project import Project
from app.models.task import Task
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember
from app.repositories.project import ProjectRepository
from app.repositories.task import TaskRepository
from app.repositories.workspace_member import WorkspaceMemberRepository
from app.services.user import UserService
from app.services.workspace import WorkspaceService

DbSession = Annotated[AsyncSession, Depends(get_db)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
BearerToken = Annotated[str, Depends(oauth2_scheme)]


async def get_current_user(
    token: BearerToken,
    session: DbSession,
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_token(token)
    except ValueError as error:
        raise credentials_exception from error

    if payload.get("type") != "access":
        raise credentials_exception

    subject = payload.get("sub")

    if subject is None:
        raise credentials_exception

    try:
        user_id = int(str(subject))
    except ValueError as error:
        raise credentials_exception from error

    user_service = UserService(session)
    user = await user_service.get_user(user_id)

    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )

    return current_user


async def get_workspace_member(
    workspace_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: DbSession,
) -> WorkspaceMember:
    member_repository = WorkspaceMemberRepository(session)

    member = await member_repository.get_by_workspace_and_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    return member


async def get_workspace_with_access(
    workspace_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: DbSession,
) -> Workspace:
    workspace_service = WorkspaceService(session)

    return await workspace_service.get_workspace(
        current_user=current_user,
        workspace_id=workspace_id,
    )


async def require_workspace_owner(
    workspace_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: DbSession,
) -> WorkspaceMember:
    member_repository = WorkspaceMemberRepository(session)

    member = await member_repository.get_by_workspace_and_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )

    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    if member.role != WorkspaceRole.OWNER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only workspace owners can perform this action",
        )

    return member


PROJECT_WRITE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.EDITOR}


async def get_project_with_access(
    workspace_id: int,
    project_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: DbSession,
) -> Project:
    member_repo = WorkspaceMemberRepository(session)
    project_repo = ProjectRepository(session)

    member = await member_repo.get_by_workspace_and_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    project = await project_repo.get_by_workspace(
        project_id=project_id,
        workspace_id=workspace_id,
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project

async def get_task_with_access(
    workspace_id: int,
    project_id: int,
    task_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: DbSession,
) -> Task:
    member_repo = WorkspaceMemberRepository(session)
    project_repo = ProjectRepository(session)
    task_repo = TaskRepository(session)

    member = await member_repo.get_by_workspace_and_user(
        workspace_id=workspace_id,
        user_id=current_user.id,
    )
    if member is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not a member of this workspace",
        )

    project = await project_repo.get_by_workspace(
        project_id=project_id,
        workspace_id=workspace_id,
    )
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    task = await task_repo.get_by_project(
        task_id=task_id,
        project_id=project_id,
    )
    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return task
