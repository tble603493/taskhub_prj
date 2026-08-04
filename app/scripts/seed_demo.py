import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.db.session import AsyncSessionLocal
from app.models.comment import Comment
from app.models.enums import ProjectStatus, TaskPriority, TaskStatus, WorkspaceRole
from app.models.label import Label
from app.models.project import Project
from app.models.task import Task
from app.models.task_label import TaskLabel
from app.models.user import User
from app.models.workspace import Workspace
from app.models.workspace_member import WorkspaceMember

DEMO_PASSWORD = "demo123456"


async def get_or_create_user(
    session: AsyncSession,
    *,
    email: str,
    full_name: str,
) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None:
        return user

    user = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(DEMO_PASSWORD),
        is_active=True,
    )
    session.add(user)
    await session.flush()

    return user


async def get_or_create_workspace(
    session: AsyncSession,
    *,
    name: str,
    description: str,
) -> Workspace:
    workspace = await session.scalar(select(Workspace).where(Workspace.name == name))
    if workspace is not None:
        return workspace

    workspace = Workspace(name=name, description=description)
    session.add(workspace)
    await session.flush()

    return workspace


async def get_or_create_member(
    session: AsyncSession,
    *,
    workspace: Workspace,
    user: User,
    role: WorkspaceRole,
) -> WorkspaceMember:
    member = await session.scalar(
        select(WorkspaceMember).where(
            WorkspaceMember.workspace_id == workspace.id,
            WorkspaceMember.user_id == user.id,
        )
    )
    if member is not None:
        member.role = role
        return member

    member = WorkspaceMember(
        workspace_id=workspace.id,
        user_id=user.id,
        role=role,
    )
    session.add(member)
    await session.flush()

    return member


async def get_or_create_project(
    session: AsyncSession,
    *,
    workspace: Workspace,
    name: str,
    description: str,
    status: ProjectStatus,
) -> Project:
    project = await session.scalar(
        select(Project).where(
            Project.workspace_id == workspace.id,
            Project.name == name,
        )
    )
    if project is not None:
        project.status = status
        return project

    project = Project(
        workspace_id=workspace.id,
        name=name,
        description=description,
        status=status,
    )
    session.add(project)
    await session.flush()

    return project


async def get_or_create_label(
    session: AsyncSession,
    *,
    project: Project,
    name: str,
    color: str,
) -> Label:
    label = await session.scalar(
        select(Label).where(
            Label.project_id == project.id,
            Label.name == name,
        )
    )
    if label is not None:
        label.color = color
        return label

    label = Label(project_id=project.id, name=name, color=color)
    session.add(label)
    await session.flush()

    return label


async def get_or_create_task(
    session: AsyncSession,
    *,
    project: Project,
    title: str,
    description: str,
    status: TaskStatus,
    priority: TaskPriority,
    created_by: User,
    assignee: User | None,
) -> Task:
    task = await session.scalar(
        select(Task).where(
            Task.project_id == project.id,
            Task.title == title,
        )
    )
    if task is not None:
        task.status = status
        task.priority = priority
        task.assignee_id = assignee.id if assignee else None
        return task

    task = Task(
        project_id=project.id,
        title=title,
        description=description,
        status=status,
        priority=priority,
        created_by_id=created_by.id,
        assignee_id=assignee.id if assignee else None,
    )
    session.add(task)
    await session.flush()

    return task


async def attach_label_once(
    session: AsyncSession,
    *,
    task: Task,
    label: Label,
) -> None:
    existing = await session.scalar(
        select(TaskLabel).where(
            TaskLabel.task_id == task.id,
            TaskLabel.label_id == label.id,
        )
    )
    if existing is not None:
        return

    session.add(TaskLabel(task_id=task.id, label_id=label.id))
    await session.flush()


async def create_comment_once(
    session: AsyncSession,
    *,
    task: Task,
    author: User,
    content: str,
) -> None:
    existing = await session.scalar(
        select(Comment).where(
            Comment.task_id == task.id,
            Comment.author_id == author.id,
            Comment.content == content,
        )
    )
    if existing is not None:
        return

    session.add(
        Comment(
            task_id=task.id,
            author_id=author.id,
            content=content,
        )
    )
    await session.flush()


async def seed_demo() -> None:
    async with AsyncSessionLocal() as session:
        owner = await get_or_create_user(
            session,
            email="demo.owner@taskhub.local",
            full_name="Demo Owner",
        )
        editor = await get_or_create_user(
            session,
            email="demo.editor@taskhub.local",
            full_name="Demo Editor",
        )
        viewer = await get_or_create_user(
            session,
            email="demo.viewer@taskhub.local",
            full_name="Demo Viewer",
        )

        workspace = await get_or_create_workspace(
            session,
            name="TaskHub Demo Workspace",
            description="Demo workspace for Swagger and manual testing.",
        )

        await get_or_create_member(
            session,
            workspace=workspace,
            user=owner,
            role=WorkspaceRole.OWNER,
        )
        await get_or_create_member(
            session,
            workspace=workspace,
            user=editor,
            role=WorkspaceRole.EDITOR,
        )
        await get_or_create_member(
            session,
            workspace=workspace,
            user=viewer,
            role=WorkspaceRole.VIEWER,
        )

        active_project = await get_or_create_project(
            session,
            workspace=workspace,
            name="Demo Active Project",
            description="Active project with tasks, labels and comments.",
            status=ProjectStatus.ACTIVE,
        )
        await get_or_create_project(
            session,
            workspace=workspace,
            name="Demo Archived Project",
            description="Archived project for permission checks.",
            status=ProjectStatus.ARCHIVED,
        )

        bug_label = await get_or_create_label(
            session,
            project=active_project,
            name="bug",
            color="#ef4444",
        )
        backend_label = await get_or_create_label(
            session,
            project=active_project,
            name="backend",
            color="#2563eb",
        )

        todo_task = await get_or_create_task(
            session,
            project=active_project,
            title="Review API error format",
            description="Check unified error response and request id.",
            status=TaskStatus.TODO,
            priority=TaskPriority.HIGH,
            created_by=owner,
            assignee=editor,
        )
        doing_task = await get_or_create_task(
            session,
            project=active_project,
            title="Verify task list cache",
            description="Check Redis cache key and invalidation behavior.",
            status=TaskStatus.IN_PROGRESS,
            priority=TaskPriority.MEDIUM,
            created_by=owner,
            assignee=owner,
        )

        await attach_label_once(session, task=todo_task, label=backend_label)
        await attach_label_once(session, task=doing_task, label=bug_label)
        await create_comment_once(
            session,
            task=todo_task,
            author=owner,
            content="Demo comment from owner.",
        )
        await create_comment_once(
            session,
            task=todo_task,
            author=editor,
            content="Demo comment from editor.",
        )

        await session.commit()


def main() -> None:
    asyncio.run(seed_demo())
    print(
        "Demo data seeded. Users: demo.owner@taskhub.local, "
        "demo.editor@taskhub.local, demo.viewer@taskhub.local. "
        f"Password: {DEMO_PASSWORD}"
    )


if __name__ == "__main__":
    main()
