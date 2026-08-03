from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import TaskPriority, TaskStatus, WorkspaceRole


def unique_email() -> str:
    return f"task-filter-{uuid4().hex}@example.com"


def response_dict(response_json: object) -> dict[str, object]:
    assert isinstance(response_json, dict)
    return cast(dict[str, object], response_json)


def object_id(data: dict[str, object]) -> int:
    value = data["id"]
    assert isinstance(value, int)
    return value


def register_and_login(
    client: TestClient,
) -> tuple[str, dict[str, str], int]:
    email = unique_email()
    password = "password123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Task Filter Test User",
        },
    )
    assert register_response.status_code == 201
    user_id = object_id(response_dict(register_response.json()))

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200
    tokens = response_dict(login_response.json())
    access_token = tokens["access_token"]
    assert isinstance(access_token, str)

    return email, {"Authorization": f"Bearer {access_token}"}, user_id


def create_workspace(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "name": f"Workspace {uuid4().hex}",
            "description": "Task filter test workspace",
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def create_project(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=headers,
        json={
            "name": f"Project {uuid4().hex}",
            "description": "Task filter test project",
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def add_member(
    client: TestClient,
    owner_headers: dict[str, str],
    workspace_id: int,
    email: str,
    role: WorkspaceRole,
) -> None:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={
            "email": email,
            "role": role,
        },
    )
    assert response.status_code == 201


def create_task(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    *,
    title: str,
    priority: TaskPriority = TaskPriority.MEDIUM,
    assignee_id: int | None = None,
) -> dict[str, object]:
    due_date = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": title,
            "description": "Task filter test task",
            "priority": priority,
            "due_date": due_date,
            "assignee_id": assignee_id,
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def update_task_status(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    task_id: int,
    status: TaskStatus,
) -> None:
    response = client.patch(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
        headers=headers,
        json={
            "status": status,
        },
    )
    assert response.status_code == 200


def setup_filter_data(
    client: TestClient,
) -> tuple[dict[str, str], int, int, int, dict[str, dict[str, object]]]:
    owner_email, owner_headers, owner_id = register_and_login(client)
    workspace = create_workspace(client, owner_headers)
    workspace_id = object_id(workspace)
    project = create_project(client, owner_headers, workspace_id)
    project_id = object_id(project)

    member_email, _, member_id = register_and_login(client)
    add_member(
        client,
        owner_headers,
        workspace_id,
        member_email,
        WorkspaceRole.EDITOR,
    )
    assert owner_email != member_email

    todo_high = create_task(
        client,
        owner_headers,
        workspace_id,
        project_id,
        title="TODO HIGH",
        priority=TaskPriority.HIGH,
        assignee_id=owner_id,
    )
    in_progress_high = create_task(
        client,
        owner_headers,
        workspace_id,
        project_id,
        title="IN PROGRESS HIGH",
        priority=TaskPriority.HIGH,
        assignee_id=member_id,
    )
    done_low = create_task(
        client,
        owner_headers,
        workspace_id,
        project_id,
        title="DONE LOW",
        priority=TaskPriority.LOW,
        assignee_id=member_id,
    )

    update_task_status(
        client,
        owner_headers,
        workspace_id,
        project_id,
        object_id(in_progress_high),
        TaskStatus.IN_PROGRESS,
    )
    update_task_status(
        client,
        owner_headers,
        workspace_id,
        project_id,
        object_id(done_low),
        TaskStatus.DONE,
    )

    tasks_by_name = {
        "todo_high": todo_high,
        "in_progress_high": in_progress_high,
        "done_low": done_low,
    }

    return owner_headers, workspace_id, project_id, member_id, tasks_by_name


def list_tasks(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    params: dict[str, object],
) -> dict[str, object]:
    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        params=params,
    )
    assert response.status_code == 200
    return response_dict(response.json())


def item_ids(data: dict[str, object]) -> set[object]:
    items = data["items"]
    assert isinstance(items, list)
    return {
        response_dict(item)["id"]
        for item in items
    }


def test_filter_tasks_by_status() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, _, tasks = setup_filter_data(client)

        data = list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"status": TaskStatus.IN_PROGRESS},
        )

    assert data["total"] == 1
    assert item_ids(data) == {tasks["in_progress_high"]["id"]}


def test_filter_tasks_by_priority() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, _, tasks = setup_filter_data(client)

        data = list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"priority": TaskPriority.HIGH},
        )

    assert data["total"] == 2
    assert item_ids(data) == {
        tasks["todo_high"]["id"],
        tasks["in_progress_high"]["id"],
    }


def test_filter_tasks_by_assignee_id() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, member_id, tasks = setup_filter_data(client)

        data = list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"assignee_id": member_id},
        )

    assert data["total"] == 2
    assert item_ids(data) == {
        tasks["in_progress_high"]["id"],
        tasks["done_low"]["id"],
    }


def test_filter_tasks_by_status_priority_and_assignee_id() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, member_id, tasks = setup_filter_data(client)

        data = list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "assignee_id": member_id,
            },
        )

    assert data["total"] == 1
    assert item_ids(data) == {tasks["in_progress_high"]["id"]}


def test_task_filter_pagination_metadata_uses_filtered_total() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, _, _ = setup_filter_data(client)

        page_one = list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {
                "priority": TaskPriority.HIGH,
                "page": 1,
                "limit": 1,
            },
        )
        page_two = list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {
                "priority": TaskPriority.HIGH,
                "page": 2,
                "limit": 1,
            },
        )

    assert page_one["total"] == 2
    assert page_one["page"] == 1
    assert page_one["limit"] == 1
    assert page_one["pages"] == 2
    assert len(cast(list[object], page_one["items"])) == 1
    assert page_two["total"] == 2
    assert page_two["page"] == 2
    assert page_two["pages"] == 2
    assert len(cast(list[object], page_two["items"])) == 1
