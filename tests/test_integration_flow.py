from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import WorkspaceRole


def unique_email(role: str) -> str:
    return f"integration-{role}-{uuid4().hex}@example.com"


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
    *,
    role: str,
) -> tuple[str, dict[str, str], int]:
    email = unique_email(role)
    password = "password123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": f"Integration {role.title()}",
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


def test_main_integration_flow() -> None:
    with TestClient(app) as client:
        owner_email, owner_headers, _ = register_and_login(client, role="owner")
        editor_email, _, editor_id = register_and_login(client, role="editor")
        viewer_email, viewer_headers, _ = register_and_login(client, role="viewer")

        workspace_response = client.post(
            "/api/v1/workspaces",
            headers=owner_headers,
            json={
                "name": f"Integration Workspace {uuid4().hex}",
                "description": "Integration flow workspace",
            },
        )
        assert workspace_response.status_code == 201
        workspace_id = object_id(response_dict(workspace_response.json()))

        for email, role in [
            (editor_email, WorkspaceRole.EDITOR),
            (viewer_email, WorkspaceRole.VIEWER),
        ]:
            add_member_response = client.post(
                f"/api/v1/workspaces/{workspace_id}/members",
                headers=owner_headers,
                json={"email": email, "role": role},
            )
            assert add_member_response.status_code == 201

        project_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects",
            headers=owner_headers,
            json={
                "name": f"Integration Project {uuid4().hex}",
                "description": "Integration flow project",
            },
        )
        assert project_response.status_code == 201
        project_id = object_id(response_dict(project_response.json()))

        task_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
            headers=owner_headers,
            json={
                "title": f"Integration Task {uuid4().hex}",
                "description": "Integration flow task",
                "priority": "HIGH",
            },
        )
        assert task_response.status_code == 201
        task_id = object_id(response_dict(task_response.json()))

        assign_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
            headers=owner_headers,
            json={"assignee_id": editor_id, "status": "IN_PROGRESS"},
        )
        assert assign_response.status_code == 200
        assert assign_response.json()["assignee_id"] == editor_id

        label_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
            headers=owner_headers,
            json={"name": f"integration-{uuid4().hex}", "color": "#22c55e"},
        )
        assert label_response.status_code == 201
        label_id = object_id(response_dict(label_response.json()))

        attach_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/labels",
            headers=owner_headers,
            json={"label_id": label_id},
        )
        assert attach_response.status_code == 201

        owner_comment_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
            headers=owner_headers,
            json={"content": f"Owner integration comment {uuid4().hex}"},
        )
        assert owner_comment_response.status_code == 201

        list_task_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
            headers=owner_headers,
            params={"status": "IN_PROGRESS", "priority": "HIGH"},
        )
        assert list_task_response.status_code == 200
        task_list = response_dict(list_task_response.json())
        assert task_list["total"] == 1

        viewer_project_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}",
            headers=viewer_headers,
        )
        assert viewer_project_response.status_code == 200

        viewer_task_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
            headers=viewer_headers,
        )
        assert viewer_task_response.status_code == 200

        viewer_comments_response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
            headers=viewer_headers,
        )
        assert viewer_comments_response.status_code == 200
        assert len(response_list(viewer_comments_response.json())) == 1

        viewer_update_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
            headers=viewer_headers,
            json={"title": "Viewer cannot update"},
        )
        assert viewer_update_response.status_code == 403

        viewer_comment_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments",
            headers=viewer_headers,
            json={"content": f"Viewer integration comment {uuid4().hex}"},
        )
        assert viewer_comment_response.status_code == 201
        viewer_comment_id = object_id(response_dict(viewer_comment_response.json()))

        delete_own_comment_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}/comments/{viewer_comment_id}",
            headers=viewer_headers,
        )
        assert delete_own_comment_response.status_code == 204

        assert owner_email.startswith("integration-owner-")
