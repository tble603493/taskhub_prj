from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.models.enums import WorkspaceRole


def unique_email() -> str:
    return f"workspace-{uuid4().hex}@example.com"


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
            "full_name": "Workspace Test User",
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
            "description": "Workspace test description",
        },
    )

    assert response.status_code == 201

    data: dict[str, object] = response.json()

    return data


def test_create_workspace_returns_201() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)

        response = client.post(
            "/api/v1/workspaces",
            headers=headers,
            json={
                "name": "My Workspace",
                "description": "Test workspace",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "My Workspace"
    assert data["description"] == "Test workspace"
    assert "id" in data


def test_create_workspace_creates_owner_member() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=headers,
        )

    assert response.status_code == 200

    members = response.json()

    assert len(members) == 1
    assert members[0]["role"] == WorkspaceRole.OWNER
    assert members[0]["workspace_id"] == workspace["id"]


def test_list_workspaces_only_returns_current_user_workspaces() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        _, other_headers = register_and_login(client)

        owner_workspace = create_workspace(
            client,
            headers=owner_headers,
            name="Owner Workspace",
        )

        create_workspace(
            client,
            headers=other_headers,
            name="Other Workspace",
        )

        response = client.get(
            "/api/v1/workspaces",
            headers=owner_headers,
        )

    assert response.status_code == 200

    data = response.json()
    workspace_ids = {workspace["id"] for workspace in data["items"]}

    assert owner_workspace["id"] in workspace_ids


def test_get_workspace_returns_200_for_member() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}",
            headers=headers,
        )

    assert response.status_code == 200
    assert response.json()["id"] == workspace["id"]


def test_update_workspace_as_owner_returns_200() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        response = client.patch(
            f"/api/v1/workspaces/{workspace['id']}",
            headers=headers,
            json={
                "name": "Updated Workspace",
            },
        )

    assert response.status_code == 200
    assert response.json()["name"] == "Updated Workspace"


def test_delete_workspace_as_owner_returns_204() -> None:
    with TestClient(app) as client:
        _, headers = register_and_login(client)
        workspace = create_workspace(client, headers=headers)

        delete_response = client.delete(
            f"/api/v1/workspaces/{workspace['id']}",
            headers=headers,
        )

        get_response = client.get(
            f"/api/v1/workspaces/{workspace['id']}",
            headers=headers,
        )

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


def test_non_member_cannot_access_workspace() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        _, other_headers = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}",
            headers=other_headers,
        )

    assert response.status_code in {403, 404}


def test_add_member_by_email_returns_201() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        member_email, _ = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)

        response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
            json={
                "email": member_email,
                "role": WorkspaceRole.VIEWER,
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["workspace_id"] == workspace["id"]
    assert data["role"] == WorkspaceRole.VIEWER


def test_add_duplicate_member_returns_409() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        member_email, _ = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)

        first_response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
            json={
                "email": member_email,
                "role": WorkspaceRole.VIEWER,
            },
        )

        second_response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
            json={
                "email": member_email,
                "role": WorkspaceRole.VIEWER,
            },
        )

    assert first_response.status_code == 201
    assert second_response.status_code == 409


def test_list_members_returns_owner_and_added_member() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        member_email, _ = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)

        client.post(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
            json={
                "email": member_email,
                "role": WorkspaceRole.EDITOR,
            },
        )

        response = client.get(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
        )

    assert response.status_code == 200

    members = response.json()
    roles = {member["role"] for member in members}

    assert len(members) == 2
    assert WorkspaceRole.OWNER in roles
    assert WorkspaceRole.EDITOR in roles


def test_remove_member_returns_204() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        member_email, _ = register_and_login(client)

        workspace = create_workspace(client, headers=owner_headers)

        add_response = client.post(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
            json={
                "email": member_email,
                "role": WorkspaceRole.VIEWER,
            },
        )

        member_id = add_response.json()["id"]

        response = client.delete(
            f"/api/v1/workspaces/{workspace['id']}/members/{member_id}",
            headers=owner_headers,
        )

    assert response.status_code == 204


def test_cannot_remove_last_owner() -> None:
    with TestClient(app) as client:
        _, owner_headers = register_and_login(client)
        workspace = create_workspace(client, headers=owner_headers)

        members_response = client.get(
            f"/api/v1/workspaces/{workspace['id']}/members",
            headers=owner_headers,
        )

        owner_member = members_response.json()[0]

        response = client.delete(
            f"/api/v1/workspaces/{workspace['id']}/members/{owner_member['id']}",
            headers=owner_headers,
        )

    assert response.status_code == 400
