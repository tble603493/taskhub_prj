from fastapi import HTTPException, status

from app.models.comment import Comment
from app.models.enums import WorkspaceRole
from app.models.user import User
from app.models.workspace_member import WorkspaceMember

WORKSPACE_OWNER_ROLES = {WorkspaceRole.OWNER}
CONTENT_WRITE_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.EDITOR}
READ_ROLES = {WorkspaceRole.OWNER, WorkspaceRole.EDITOR, WorkspaceRole.VIEWER}


def require_workspace_roles(
    member: WorkspaceMember,
    allowed_roles: set[WorkspaceRole],
    detail: str = "Not enough permissions",
) -> None:
    if member.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


def require_workspace_owner(member: WorkspaceMember) -> None:
    require_workspace_roles(
        member=member,
        allowed_roles=WORKSPACE_OWNER_ROLES,
        detail="Only workspace owners can perform this action",
    )


def require_content_write(member: WorkspaceMember) -> None:
    require_workspace_roles(
        member=member,
        allowed_roles=CONTENT_WRITE_ROLES,
        detail="Not enough permissions to modify this resource",
    )


def can_delete_comment(
    current_user: User,
    member: WorkspaceMember,
    comment: Comment,
) -> bool:
    return comment.author_id == current_user.id or member.role in CONTENT_WRITE_ROLES
