from fastapi.testclient import TestClient

from app.main import app


def test_get_me_returns_200() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == "dev@example.com"
    assert data["full_name"] is not None


def test_get_me_does_not_return_hashed_password() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")

    assert response.status_code == 200

    data = response.json()

    assert "hashed_password" not in data
    assert "password" not in data


def test_patch_me_updates_full_name() -> None:
    with TestClient(app) as client:
        original_response = client.get("/api/v1/users/me")
        original_name = original_response.json()["full_name"]

        response = client.patch(
            "/api/v1/users/me",
            json={
                "full_name": "Updated Dev User",
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["full_name"] == "Updated Dev User"
        assert "hashed_password" not in data

        client.patch(
            "/api/v1/users/me",
            json={
                "full_name": original_name,
            },
        )


def test_patch_me_rejects_invalid_email() -> None:
    with TestClient(app) as client:
        response = client.patch(
            "/api/v1/users/me",
            json={
                "email": "not-an-email",
            },
        )

    assert response.status_code == 422
