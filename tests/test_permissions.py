from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import ProjectStatus, TaskPriority, WorkspaceRole


def unique_email() -> str:
    return f"permission-{uuid4().hex}@example.com"


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
            "full_name": "Permission Test User",
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
            "description": "Permission test workspace",
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
            "description": "Permission test project",
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
            "description": "Permission test task",
            "priority": TaskPriority.MEDIUM,
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def create_label(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
        headers=headers,
        json={
            "name": f"Label {uuid4().hex}",
            "color": "#64748b",
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
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
        headers=headers,
        json={
            "content": "Permission test comment",
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
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={
            "email": email,
            "role": role,
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def setup_workspace_content(
    client: TestClient,
) -> tuple[dict[str, str], int, int, int, int, int]:
    _, owner_headers, _ = register_and_login(client)
    workspace_id = object_id(create_workspace(client, owner_headers))
    project_id = object_id(create_project(client, owner_headers, workspace_id))
    task_id = object_id(create_task(client, owner_headers, workspace_id, project_id))
    label_id = object_id(create_label(client, owner_headers, workspace_id, project_id))
    comment_id = object_id(
        create_comment(
            client,
            owner_headers,
            workspace_id,
            project_id,
            task_id,
        )
    )
    return owner_headers, workspace_id, project_id, task_id, label_id, comment_id


def test_protected_endpoint_without_token_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_inactive_user_returns_403_on_active_user_endpoint() -> None:
    with TestClient(app) as client:
        _, headers, _ = register_and_login(client)

        deactivate_response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json={
                "is_active": False,
            },
        )
        response = client.get("/api/v1/users/me", headers=headers)

    assert deactivate_response.status_code == 200
    assert response.status_code == 403


def test_non_member_cannot_access_workspace_scoped_resources() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id, label_id, comment_id = (
            setup_workspace_content(client)
        )
        _, outsider_headers, _ = register_and_login(client)

        responses = [
            client.get(f"/api/v1/workspaces/{workspace_id}", headers=outsider_headers),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
                headers=outsider_headers,
            ),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
                headers=outsider_headers,
            ),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
                headers=outsider_headers,
            ),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
                headers=outsider_headers,
            ),
        ]

    assert owner_headers
    assert comment_id
    assert {response.status_code for response in responses} <= {403, 404}


def test_viewer_can_read_project_task_label_and_comment() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id, label_id, _ = (
            setup_workspace_content(client)
        )
        viewer_email, viewer_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            viewer_email,
            WorkspaceRole.VIEWER,
        )

        responses = [
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
                headers=viewer_headers,
            ),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
                headers=viewer_headers,
            ),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
                headers=viewer_headers,
            ),
            client.get(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
                headers=viewer_headers,
            ),
        ]

    assert [response.status_code for response in responses] == [200, 200, 200, 200]


def test_viewer_cannot_write_project_task_or_label() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id, label_id, _ = (
            setup_workspace_content(client)
        )
        viewer_email, viewer_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            viewer_email,
            WorkspaceRole.VIEWER,
        )

        responses = [
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects",
                headers=viewer_headers,
                json={"name": "Viewer Project"},
            ),
            client.patch(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
                headers=viewer_headers,
                json={"description": "Viewer project update"},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
                headers=viewer_headers,
                json={"title": "Viewer Task"},
            ),
            client.patch(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
                headers=viewer_headers,
                json={"title": "Viewer task update"},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
                headers=viewer_headers,
                json={"name": "Viewer Label"},
            ),
            client.patch(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
                headers=viewer_headers,
                json={"name": "Viewer label update"},
            ),
        ]

    assert [response.status_code for response in responses] == [403] * len(responses)


def test_editor_can_write_content_but_cannot_manage_members_or_delete_project() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id, label_id, _ = (
            setup_workspace_content(client)
        )
        editor_email, editor_headers, _ = register_and_login(client)
        other_email, _, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            editor_email,
            WorkspaceRole.EDITOR,
        )

        create_project_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects",
            headers=editor_headers,
            json={"name": f"Editor Project {uuid4().hex}"},
        )
        update_task_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
            headers=editor_headers,
            json={"title": "Editor task update"},
        )
        update_label_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label_id}",
            headers=editor_headers,
            json={"name": f"Editor Label {uuid4().hex}"},
        )
        add_member_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=editor_headers,
            json={"email": other_email, "role": WorkspaceRole.VIEWER},
        )
        delete_project_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
            headers=editor_headers,
        )

    assert create_project_response.status_code == 201
    assert update_task_response.status_code == 200
    assert update_label_response.status_code == 200
    assert add_member_response.status_code == 403
    assert delete_project_response.status_code == 403


def test_owner_can_manage_member_and_cannot_remove_last_owner() -> None:
    with TestClient(app) as client:
        _, owner_headers, _ = register_and_login(client)
        workspace_id = object_id(create_workspace(client, owner_headers))
        member_email, _, _ = register_and_login(client)

        add_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
            json={"email": member_email, "role": WorkspaceRole.EDITOR},
        )
        members_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/members",
            headers=owner_headers,
        )
        members = response_list(members_response.json())
        owner_member = next(
            member
            for member in members
            if member["role"] == WorkspaceRole.OWNER
        )
        remove_owner_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/members/{owner_member['id']}",
            headers=owner_headers,
        )

    assert add_response.status_code == 201
    assert remove_owner_response.status_code == 400


def test_comment_ownership_and_moderation_policy() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id, _, _ = (
            setup_workspace_content(client)
        )
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

        own_comment = create_comment(
            client,
            viewer_headers,
            workspace_id,
            project_id,
            task_id,
        )
        delete_own_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{own_comment['id']}",
            headers=viewer_headers,
        )

        owner_comment = create_comment(
            client,
            owner_headers,
            workspace_id,
            project_id,
            task_id,
        )
        viewer_delete_other_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{owner_comment['id']}",
            headers=viewer_headers,
        )
        editor_delete_other_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{owner_comment['id']}",
            headers=editor_headers,
        )

    assert delete_own_response.status_code == 204
    assert viewer_delete_other_response.status_code == 403
    assert editor_delete_other_response.status_code == 204


def test_archived_project_blocks_content_mutations() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id, task_id, label_id, _ = (
            setup_workspace_content(client)
        )

        archive_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/archive",
            headers=owner_headers,
        )
        archived = response_dict(archive_response.json())

        responses = [
            client.patch(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
                headers=owner_headers,
                json={"description": "Archived update"},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
                headers=owner_headers,
                json={"title": "Archived task"},
            ),
            client.patch(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
                headers=owner_headers,
                json={"title": "Archived task update"},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
                headers=owner_headers,
                json={"name": "Archived label"},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/labels",
                headers=owner_headers,
                json={"label_id": label_id},
            ),
            client.post(
                f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
                headers=owner_headers,
                json={"content": "Archived comment"},
            ),
        ]

    assert archive_response.status_code == 200
    assert archived["status"] == ProjectStatus.ARCHIVED
    assert [response.status_code for response in responses] == [409] * len(responses)
