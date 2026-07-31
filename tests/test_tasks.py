from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import ProjectStatus, TaskPriority, TaskStatus, WorkspaceRole


def unique_email() -> str:
    return f"task-{uuid4().hex}@example.com"


def object_id(data: dict[str, object]) -> int:
    value = data["id"]
    assert isinstance(value, int)
    return value


def register_and_login(client: TestClient) -> tuple[str, dict[str, str], int]:
    email = unique_email()
    password = "password123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Task Test User",
        },
    )
    assert register_response.status_code == 201
    user_id = register_response.json()["id"]
    assert isinstance(user_id, int)

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )
    assert login_response.status_code == 200

    return email, {
        "Authorization": f"Bearer {login_response.json()['access_token']}",
    }, user_id


def create_workspace(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "name": f"Workspace {uuid4().hex}",
            "description": "Task test workspace",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, dict)
    return data


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
            "description": "Task test project",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, dict)
    return data


def create_task(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    **payload: object,
) -> dict[str, object]:
    body: dict[str, object] = {
        "title": f"Task {uuid4().hex}",
        "description": "Task test description",
        "priority": TaskPriority.MEDIUM,
    }
    body.update(payload)

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        json=body,
    )
    assert response.status_code == 201
    data = response.json()
    assert isinstance(data, dict)
    return data


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


def setup_project(client: TestClient) -> tuple[dict[str, str], int, int, int]:
    _, headers, user_id = register_and_login(client)
    workspace = create_workspace(client, headers)
    workspace_id = object_id(workspace)
    project = create_project(client, headers, workspace_id)
    project_id = object_id(project)
    return headers, user_id, workspace_id, project_id


def test_create_task_returns_201_and_sets_created_by() -> None:
    with TestClient(app) as client:
        headers, user_id, workspace_id, project_id = setup_project(client)

        task = create_task(
            client,
            headers,
            workspace_id,
            project_id,
            title="Create Task Test",
        )

    assert task["title"] == "Create Task Test"
    assert task["project_id"] == project_id
    assert task["created_by_id"] == user_id
    assert task["status"] == TaskStatus.TODO


def test_list_tasks_returns_project_tasks() -> None:
    with TestClient(app) as client:
        headers, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)

        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
            headers=headers,
        )

    assert response.status_code == 200
    data = response.json()
    task_ids = {item["id"] for item in data["items"]}
    assert task["id"] in task_ids


def test_get_task_returns_200_for_member() -> None:
    with TestClient(app) as client:
        headers, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)

        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["id"] == task["id"]


def test_update_task_fields_returns_200() -> None:
    with TestClient(app) as client:
        headers, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        due_date = (datetime.now(UTC) + timedelta(days=3)).isoformat()

        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={
                "title": "Updated Task",
                "description": "Updated description",
                "status": TaskStatus.IN_PROGRESS,
                "priority": TaskPriority.HIGH,
                "due_date": due_date,
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Updated Task"
    assert data["description"] == "Updated description"
    assert data["status"] == TaskStatus.IN_PROGRESS
    assert data["priority"] == TaskPriority.HIGH
    assert data["due_date"] is not None


def test_assign_task_to_workspace_member_returns_200() -> None:
    with TestClient(app) as client:
        owner_headers, _, workspace_id, project_id = setup_project(client)
        member_email, _, member_id = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            member_email,
            WorkspaceRole.VIEWER,
        )

        task = create_task(client, owner_headers, workspace_id, project_id)

        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=owner_headers,
            json={
                "assignee_id": member_id,
            },
        )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == member_id


def test_assign_task_to_non_member_returns_400() -> None:
    with TestClient(app) as client:
        owner_headers, _, workspace_id, project_id = setup_project(client)
        _, _, outsider_id = register_and_login(client)
        task = create_task(client, owner_headers, workspace_id, project_id)

        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=owner_headers,
            json={
                "assignee_id": outsider_id,
            },
        )

    assert response.status_code == 400


def test_non_member_cannot_access_task() -> None:
    with TestClient(app) as client:
        owner_headers, _, workspace_id, project_id = setup_project(client)
        _, outsider_headers, _ = register_and_login(client)
        task = create_task(client, owner_headers, workspace_id, project_id)

        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=outsider_headers,
        )

    assert response.status_code == 403


def test_viewer_cannot_create_update_or_delete_task() -> None:
    with TestClient(app) as client:
        owner_headers, _, workspace_id, project_id = setup_project(client)
        viewer_email, viewer_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            viewer_email,
            WorkspaceRole.VIEWER,
        )
        task = create_task(client, owner_headers, workspace_id, project_id)

        create_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
            headers=viewer_headers,
            json={"title": "Viewer Task"},
        )
        update_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=viewer_headers,
            json={"title": "Viewer Update"},
        )
        delete_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=viewer_headers,
        )

    assert create_response.status_code == 403
    assert update_response.status_code == 403
    assert delete_response.status_code == 403


def test_editor_can_create_update_and_delete_task() -> None:
    with TestClient(app) as client:
        owner_headers, _, workspace_id, project_id = setup_project(client)
        editor_email, editor_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            editor_email,
            WorkspaceRole.EDITOR,
        )

        task = create_task(client, editor_headers, workspace_id, project_id)

        update_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=editor_headers,
            json={"title": "Editor Updated Task"},
        )
        delete_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=editor_headers,
        )

    assert update_response.status_code == 200
    assert update_response.json()["title"] == "Editor Updated Task"
    assert delete_response.status_code == 204


def test_cannot_create_or_update_task_in_archived_project() -> None:
    with TestClient(app) as client:
        headers, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)

        archive_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/archive",
            headers=headers,
        )
        assert archive_response.status_code == 200
        assert archive_response.json()["status"] == ProjectStatus.ARCHIVED

        create_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
            headers=headers,
            json={"title": "Task In Archived Project"},
        )
        update_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"title": "Update In Archived Project"},
        )

    assert create_response.status_code == 409
    assert update_response.status_code == 409


def test_delete_task_returns_204() -> None:
    with TestClient(app) as client:
        headers, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
        )

    assert response.status_code == 204


def test_task_response_contains_expected_fields() -> None:
    with TestClient(app) as client:
        headers, _, workspace_id, project_id = setup_project(client)

        task = create_task(client, headers, workspace_id, project_id)

    assert "project_id" in task
    assert "status" in task
    assert "priority" in task
    assert "created_by_id" in task
    assert "assignee_id" in task
    assert "created_at" in task
    assert "updated_at" in task
