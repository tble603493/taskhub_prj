from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import WorkspaceRole


def unique_email() -> str:
    return f"label-{uuid4().hex}@example.com"


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
            "full_name": "Label Test User",
        },
    )
    assert register_response.status_code == 201
    user = response_dict(register_response.json())
    user_id = object_id(user)

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
            "description": "Label test workspace",
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
            "description": "Label test project",
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
            "description": "Label test task",
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def create_label(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    name: str | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
        headers=headers,
        json={
            "name": name or f"Label {uuid4().hex}",
            "color": "#22c55e",
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


def setup_project(client: TestClient) -> tuple[dict[str, str], int, int]:
    _, headers, _ = register_and_login(client)
    workspace = create_workspace(client, headers)
    workspace_id = object_id(workspace)
    project = create_project(client, headers, workspace_id)
    project_id = object_id(project)
    return headers, workspace_id, project_id


def test_create_label_returns_201() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)

        label = create_label(
            client,
            headers,
            workspace_id,
            project_id,
            name="Backend",
        )

    assert label["name"] == "Backend"
    assert label["project_id"] == project_id
    assert label["color"] == "#22c55e"


def test_duplicate_label_name_in_project_returns_409() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        create_label(client, headers, workspace_id, project_id, name="Bug")

        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
            headers=headers,
            json={
                "name": "Bug",
                "color": "#ef4444",
            },
        )

    assert response.status_code == 409


def test_list_labels_returns_project_labels() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        label = create_label(client, headers, workspace_id, project_id)

        response = client.get(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
            headers=headers,
        )

    assert response.status_code == 200
    labels = response_list(response.json())
    label_ids = {item["id"] for item in labels}
    assert label["id"] in label_ids


def test_update_label_as_owner_returns_200() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        label = create_label(client, headers, workspace_id, project_id)

        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label['id']}",
            headers=headers,
            json={
                "name": "Updated Label",
                "color": "#3b82f6",
            },
        )

    assert response.status_code == 200
    data = response_dict(response.json())
    assert data["name"] == "Updated Label"
    assert data["color"] == "#3b82f6"


def test_viewer_cannot_create_update_or_delete_label() -> None:
    with TestClient(app) as client:
        owner_headers, workspace_id, project_id = setup_project(client)
        viewer_email, viewer_headers, _ = register_and_login(client)
        add_member(
            client,
            owner_headers,
            workspace_id,
            viewer_email,
            WorkspaceRole.VIEWER,
        )
        label = create_label(client, owner_headers, workspace_id, project_id)

        create_response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels",
            headers=viewer_headers,
            json={
                "name": "Viewer Label",
                "color": "#64748b",
            },
        )
        update_response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label['id']}",
            headers=viewer_headers,
            json={
                "name": "Viewer Update",
            },
        )
        delete_response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/labels/{label['id']}",
            headers=viewer_headers,
        )

    assert create_response.status_code == 403
    assert update_response.status_code == 403
    assert delete_response.status_code == 403


def test_attach_label_to_task_returns_201() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        label = create_label(client, headers, workspace_id, project_id)

        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}/labels",
            headers=headers,
            json={
                "label_id": label["id"],
            },
        )

    assert response.status_code == 201
    assert response_dict(response.json())["id"] == label["id"]


def test_attach_same_label_twice_is_idempotent() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        label = create_label(client, headers, workspace_id, project_id)
        url = (
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}"
            f"/tasks/{task['id']}/labels"
        )

        first_response = client.post(
            url,
            headers=headers,
            json={"label_id": label["id"]},
        )
        second_response = client.post(
            url,
            headers=headers,
            json={"label_id": label["id"]},
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 201
    assert response_dict(second_response.json())["id"] == label["id"]


def test_detach_label_from_task_returns_204() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        label = create_label(client, headers, workspace_id, project_id)
        client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}/labels",
            headers=headers,
            json={
                "label_id": label["id"],
            },
        )

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}/labels/{label['id']}",
            headers=headers,
        )

    assert response.status_code == 204


def test_cannot_attach_label_from_another_project_to_task() -> None:
    with TestClient(app) as client:
        headers, workspace_id, project_id = setup_project(client)
        other_project = create_project(client, headers, workspace_id)
        other_project_id = object_id(other_project)
        task = create_task(client, headers, workspace_id, project_id)
        other_label = create_label(
            client,
            headers,
            workspace_id,
            other_project_id,
        )

        response = client.post(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}/labels",
            headers=headers,
            json={
                "label_id": other_label["id"],
            },
        )

    assert response.status_code == 404
