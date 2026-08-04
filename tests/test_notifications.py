from typing import cast
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from httpx import Response

from app.main import app
from app.models.enums import WorkspaceRole
from app.services.notification import NotificationService


def unique_email() -> str:
    return f"notification-{uuid4().hex}@example.com"


def response_dict(response_json: object) -> dict[str, object]:
    assert isinstance(response_json, dict)
    return cast(dict[str, object], response_json)


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
            "full_name": "Notification Test User",
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


def create_workspace(client: TestClient, headers: dict[str, str]) -> int:
    response = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "name": f"Workspace {uuid4().hex}",
            "description": "Notification test workspace",
        },
    )
    assert response.status_code == 201
    return object_id(response_dict(response.json()))


def create_project(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
) -> int:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=headers,
        json={
            "name": f"Project {uuid4().hex}",
            "description": "Notification test project",
        },
    )
    assert response.status_code == 201
    return object_id(response_dict(response.json()))


def add_member(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    email: str,
) -> None:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=headers,
        json={
            "email": email,
            "role": WorkspaceRole.EDITOR,
        },
    )
    assert response.status_code == 201


def create_task(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
) -> int:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": f"Task {uuid4().hex}",
            "description": "Notification test task",
        },
    )
    assert response.status_code == 201
    return object_id(response_dict(response.json()))


def setup_task(client: TestClient) -> tuple[dict[str, str], int, int, int, int]:
    owner_headers = register_and_login(client)[1]
    workspace_id = create_workspace(client, owner_headers)
    project_id = create_project(client, owner_headers, workspace_id)
    member_email, _, member_id = register_and_login(client)
    add_member(client, owner_headers, workspace_id, member_email)
    task_id = create_task(client, owner_headers, workspace_id, project_id)

    return owner_headers, workspace_id, project_id, task_id, member_id


def patch_task(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    task_id: int,
    json: dict[str, object],
) -> Response:
    return cast(
        Response,
        client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task_id}",
            headers=headers,
            json=json,
        ),
    )


def test_update_task_with_assignee_id_triggers_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []

    def fake_notify(
        self: NotificationService,
        task_id: int,
        assignee_id: int,
    ) -> None:
        calls.append((task_id, assignee_id))

    monkeypatch.setattr(NotificationService, "notify_task_assigned", fake_notify)

    with TestClient(app) as client:
        headers, workspace_id, project_id, task_id, member_id = setup_task(client)
        response = patch_task(
            client,
            headers,
            workspace_id,
            project_id,
            task_id,
            {"assignee_id": member_id},
        )

    assert response.status_code == 200
    assert calls == [(task_id, member_id)]


def test_notification_error_does_not_fail_task_update(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_notify(
        self: NotificationService,
        task_id: int,
        assignee_id: int,
    ) -> None:
        raise RuntimeError("notification failed")

    monkeypatch.setattr(NotificationService, "notify_task_assigned", fake_notify)

    with TestClient(app) as client:
        headers, workspace_id, project_id, task_id, member_id = setup_task(client)
        response = patch_task(
            client,
            headers,
            workspace_id,
            project_id,
            task_id,
            {"assignee_id": member_id},
        )

    assert response.status_code == 200
    assert response.json()["assignee_id"] == member_id


def test_update_task_without_assignee_id_does_not_trigger_notification(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[int, int]] = []

    def fake_notify(
        self: NotificationService,
        task_id: int,
        assignee_id: int,
    ) -> None:
        calls.append((task_id, assignee_id))

    monkeypatch.setattr(NotificationService, "notify_task_assigned", fake_notify)

    with TestClient(app) as client:
        headers, workspace_id, project_id, task_id, _ = setup_task(client)
        response = patch_task(
            client,
            headers,
            workspace_id,
            project_id,
            task_id,
            {"title": "Updated without assignee"},
        )

    assert response.status_code == 200
    assert calls == []
