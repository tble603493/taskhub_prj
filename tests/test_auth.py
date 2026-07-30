from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def unique_email() -> str:
    return f"auth-{uuid4().hex}@example.com"


def register_user(
    client: TestClient,
    *,
    email: str | None = None,
    password: str = "password123",
) -> tuple[str, str]:
    user_email = email or unique_email()

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": user_email,
            "password": password,
            "full_name": "Auth Test User",
        },
    )

    assert response.status_code == 201

    return user_email, password


def login_user(
    client: TestClient,
    *,
    email: str,
    password: str,
) -> dict[str, str]:
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
    )

    assert response.status_code == 200

    data = response.json()

    return {
        "access_token": data["access_token"],
        "refresh_token": data["refresh_token"],
        "token_type": data["token_type"],
    }


def test_register_success() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": unique_email(),
                "password": "password123",
                "full_name": "Auth Test User",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["email"].startswith("auth-")
    assert data["full_name"] == "Auth Test User"
    assert "hashed_password" not in data
    assert "password" not in data


def test_register_duplicate_email_returns_409() -> None:
    with TestClient(app) as client:
        email, password = register_user(client)

        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": password,
                "full_name": "Duplicate User",
            },
        )

    assert response.status_code == 409


def test_login_with_valid_password_returns_tokens() -> None:
    with TestClient(app) as client:
        email, password = register_user(client)
        tokens = login_user(client, email=email, password=password)

    assert tokens["access_token"]
    assert tokens["refresh_token"]
    assert tokens["token_type"] == "bearer"


def test_login_with_invalid_password_returns_401() -> None:
    with TestClient(app) as client:
        email, _ = register_user(client)

        response = client.post(
            "/api/v1/auth/login",
            data={
                "username": email,
                "password": "wrong-password",
            },
        )

    assert response.status_code == 401


def test_get_me_with_access_token_returns_200() -> None:
    with TestClient(app) as client:
        email, password = register_user(client)
        tokens = login_user(client, email=email, password=password)

        response = client.get(
            "/api/v1/users/me",
            headers={
                "Authorization": f"Bearer {tokens['access_token']}",
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["email"] == email
    assert "hashed_password" not in data


def test_get_me_without_token_returns_401() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")

    assert response.status_code == 401


def test_refresh_token_returns_new_tokens() -> None:
    with TestClient(app) as client:
        email, password = register_user(client)
        tokens = login_user(client, email=email, password=password)

        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )

    assert response.status_code == 200

    data = response.json()

    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


def test_logout_revokes_refresh_token() -> None:
    with TestClient(app) as client:
        email, password = register_user(client)
        tokens = login_user(client, email=email, password=password)

        logout_response = client.post(
            "/api/v1/auth/logout",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )

        refresh_response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": tokens["refresh_token"],
            },
        )

    assert logout_response.status_code == 204
    assert refresh_response.status_code == 401
