from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import WorkspaceRole


def unique_email() -> str:
    return f"comment-{uuid4().hex}@example.com"


def response_dict(response_json: object) -> dict[str, object]:
    assert isinstance(response_json, dict)
    return cast(dict[str, object], response_json)


def response_list(response_json: object) -> list[dict[str, object]]:
    assert isinstance(response_json, list)
    return cast(list[dict[str, object]], response_json)


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
            "full_name": "Comment Test User",
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
            "description": "Comment test workspace",
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
            "description": "Comment test project",
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def create_task(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": f"Task {uuid4().hex}",
            "description": "Comment test task",
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def create_comment(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    task_id: int,
    content: str = "A useful comment",
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
        headers=headers,
        json={
            "content": content,
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


def setup_task(client: TestClient) -> tuple[dict[str, str], int, int, int]:
    _, headers, _ = register_and_login(client)
    workspace = create_workspace(client, headers)
    workspace_id = object_id(workspace)
    project = create_project(client, headers, workspace_id)
    project_id = object_id(project)
    task = create_task(client, headers, workspace_id, project_id)
    task_id = object_id(task)
    return headers, workspace_id, project_id, task_id


def test_create_comment_returns_201() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, task_id = setup_task(client)

        comment = create_comment(
            client,
            headers,
            workspace_id,
            project_id,
            task_id,
            content="First comment",
        )

    assert comment["content"] == "First comment"
    assert comment["task_id"] == task_id
    assert "author_id" in comment


def test_list_comments_returns_task_comments() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, task_id = setup_task(client)
        comment = create_comment(client, headers, workspace_id, project_id, task_id)

        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
            headers=headers,
        )

    assert response.status_code == 200
    comments = response_list(response.json())
    comment_ids = {item["id"] for item in comments}
    assert comment["id"] in comment_ids


def test_author_can_delete_own_comment() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id, task_id = setup_task(client)
        comment = create_comment(client, headers, workspace_id, project_id, task_id)

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{comment['id']}",
            headers=headers,
        )

    assert response.status_code == 204


def test_owner_can_delete_other_users_comment() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id = setup_task(client)
        member_email, member_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            member_email,
            WorkspaceRole.VIEWER,
        )
        comment = create_comment(
            client,
            member_headers,
            workspace_id,
            project_id,
            task_id,
        )

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{comment['id']}",
            headers=owner_headers,
        )

    assert response.status_code == 204


def test_editor_can_delete_other_users_comment() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id = setup_task(client)
        editor_email, editor_headers, _ = register_and_login(client)
        viewer_email, viewer_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            editor_email,
            WorkspaceRole.EDITOR,
        )
        add_member(
            client,
            owner_headers,
            workspace_id,
            viewer_email,
            WorkspaceRole.VIEWER,
        )
        comment = create_comment(
            client,
            viewer_headers,
            workspace_id,
            project_id,
            task_id,
        )

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{comment['id']}",
            headers=editor_headers,
        )

    assert response.status_code == 204


def test_viewer_cannot_delete_other_users_comment() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id = setup_task(client)
        viewer_email, viewer_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            viewer_email,
            WorkspaceRole.VIEWER,
        )
        comment = create_comment(
            client,
            owner_headers,
            workspace_id,
            project_id,
            task_id,
        )

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{comment['id']}",
            headers=viewer_headers,
        )

    assert response.status_code == 403


def test_non_member_cannot_read_or_create_comment() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id = setup_task(client)
        _, outsider_headers, _ = register_and_login(client)
        create_comment(client, owner_headers, workspace_id, project_id, task_id)

        list_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
            headers=outsider_headers,
        )
        create_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
            headers=outsider_headers,
            json={
                "content": "Outsider comment",
            },
        )

    assert list_response.status_code == 403
    assert create_response.status_code == 403
