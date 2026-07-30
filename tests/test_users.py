from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def create_auth_headers(client: TestClient) -> dict[str, str]:
    email = f"user-{uuid4().hex}@example.com"
    password = "password123"

    register_response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "User Test",
        },
    )

    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert login_response.status_code == 200

    access_token = login_response.json()["access_token"]

    return {
        "Authorization": f"Bearer {access_token}",
    }


def test_get_me_returns_200() -> None:
    with TestClient(app) as client:
        headers = create_auth_headers(client)
        response = client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert data["email"].startswith("user-")
    assert data["full_name"] == "User Test"


def test_get_me_does_not_return_hashed_password() -> None:
    with TestClient(app) as client:
        headers = create_auth_headers(client)
        response = client.get("/api/v1/users/me", headers=headers)

    assert response.status_code == 200

    data = response.json()

    assert "hashed_password" not in data
    assert "password" not in data


def test_patch_me_updates_full_name() -> None:
    with TestClient(app) as client:
        headers = create_auth_headers(client)

        response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json={
                "full_name": "Updated Test User",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["full_name"] == "Updated Test User"
    assert "hashed_password" not in data


def test_patch_me_rejects_invalid_email() -> None:
    with TestClient(app) as client:
        headers = create_auth_headers(client)

        response = client.patch(
            "/api/v1/users/me",
            headers=headers,
            json={
                "email": "not-an-email",
            },
        )

    assert response.status_code == 422
