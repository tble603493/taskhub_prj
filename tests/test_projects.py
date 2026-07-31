from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import ProjectStatus, WorkspaceRole


def unique_email() -> str:
    return f"project-{uuid4().hex}@example.com"


def object_id(data: dict[str, object]) -> int:
    value = data["id"]
    assert isinstance(value, int)
    return value


def register_and_login(
    client: TestClient,
    *,
    email: str | None = None,
    password: str = "password123",
) -> tuple[str, dict[str, str]]:
    user_email = email or unique_email()

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": user_email,
            "password": password,
            "full_name": "Project Test User",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": user_email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return user_email, {
        "Authorization": f"Bearer {access_token}",
    }


def create_workspace(
    client: TestClient,
    *,
    headers: dict[str, str],
    name: str | None = None,
) -> dict[str, object]:
    response = client.post(
        "/api/v1/workspaces",
        headers=headers,
        json={
            "name": name or f"Workspace {uuid4().hex}",
            "description": "Project test workspace",
        },
    )

    assert response.status_code == 201

    data: dict[str, object] = response.json()
    return data


def create_project(
    client: TestClient,
    *,
    headers: dict[str, str],
    workspace_id: int,
    name: str | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects",
        headers=headers,
        json={
            "name": name or f"Project {uuid4().hex}",
            "description": "Project test description",
        },
    )

    assert response.status_code == 201

    data: dict[str, object] = response.json()
    return data


def add_workspace_member(
    client: TestClient,
    *,
    owner_headers: dict[str, str],
    workspace_id: int,
    member_email: str,
    role: WorkspaceRole,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/members",
        headers=owner_headers,
        json={
            "email": member_email,
            "role": role,
        },
    )

    assert response.status_code == 201

    data: dict[str, object] = response.json()
    return data


def test_create_project_in_workspace_returns_201() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects",
            headers=headers,
            json={
                "name": "Project Create Test",
                "description": "Project description",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Project Create Test"
    assert data["workspace_id"] == workspace["id"]
    assert data["status"] == ProjectStatus.ACTIVE
    assert "created_at" in data
    assert "updated_at" in data


def test_list_projects_returns_workspace_projects() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)
        project = create_project(
            client,
            headers=headers,
            workspace_id=object_id(workspace),
            name="Listed Project",
        )

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}/projects",
            headers=headers,
        )

    assert response.status_code == 200

    data = response.json()
    project_ids = {item["id"] for item in data["items"]}

    assert data["total"] >= 1
    assert project["id"] in project_ids


def test_get_project_returns_200_for_workspace_member() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)
        project = create_project(
            client,
            headers=headers,
            workspace_id=object_id(workspace),
        )

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["id"] == project["id"]


def test_update_project_as_owner_returns_200() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)
        project = create_project(
            client,
            headers=headers,
            workspace_id=object_id(workspace),
        )

        response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}",
            headers=headers,
            json={
                "name": "Updated Project",
                "description": "Updated project description",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Updated Project"
    assert data["description"] == "Updated project description"


def test_archive_project_sets_status_archived() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)
        project = create_project(
            client,
            headers=headers,
            workspace_id=object_id(workspace),
        )

        response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/archive",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["status"] == ProjectStatus.ARCHIVED


def test_non_member_cannot_access_project() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        _, outsider_headers = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)
        project = create_project(
            client,
            headers=owner_headers,
            workspace_id=object_id(workspace),
        )

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}",
            headers=outsider_headers,
        )

    assert response.status_code == 403


def test_duplicate_project_name_in_same_workspace_returns_409() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        first_response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects",
            headers=headers,
            json={
                "name": "Duplicate Project",
                "description": "First project",
            },
        )

        second_response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects",
            headers=headers,
            json={
                "name": "Duplicate Project",
                "description": "Second project",
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_viewer_cannot_create_update_or_archive_project() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        viewer_email, viewer_headers = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)
        project = create_project(
            client,
            headers=owner_headers,
            workspace_id=object_id(workspace),
        )
        add_workspace_member(
            client,
            owner_headers=owner_headers,
            workspace_id=object_id(workspace),
            member_email=viewer_email,
            role=WorkspaceRole.VIEWER,
        )

        create_response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects",
            headers=viewer_headers,
            json={
                "name": "Viewer Project",
            },
        )

        update_response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}",
            headers=viewer_headers,
            json={
                "description": "Viewer update",
            },
        )

        archive_response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/archive",
            headers=viewer_headers,
        )

    assert create_response.status_code == 403
    assert update_response.status_code == 403
    assert archive_response.status_code == 403


def test_editor_can_create_update_and_archive_project() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        editor_email, editor_headers = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)
        add_workspace_member(
            client,
            owner_headers=owner_headers,
            workspace_id=object_id(workspace),
            member_email=editor_email,
            role=WorkspaceRole.EDITOR,
        )

        project = create_project(
            client,
            headers=editor_headers,
            workspace_id=object_id(workspace),
            name="Editor Project",
        )

        update_response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}",
            headers=editor_headers,
            json={
                "description": "Editor update",
            },
        )

        archive_response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}/projects/{project['id']}/archive",
            headers=editor_headers,
        )

    assert project["name"] == "Editor Project"
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Editor update"
    assert archive_response.status_code == 200
    assert archive_response.json()["status"] == ProjectStatus.ARCHIVED


def test_project_response_contains_expected_fields() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/projects",
            headers=headers,
            json={
                "name": "Project Response Fields",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert "workspace_id" in data
    assert "status" in data
    assert "created_at" in data
    assert "updated_at" in data
