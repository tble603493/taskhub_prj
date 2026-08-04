from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.request_context import REQUEST_ID_HEADER
from app.main import app


def response_dict(response_json: object) -> dict[str, object]:
    assert isinstance(response_json, dict)
    return cast(dict[str, object], response_json)


def register_user(client: TestClient, email: str) -> None:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "password123",
            "full_name": "Error Handling User",
        },
    )
    assert response.status_code == 201


def assert_error_shape(data: dict[str, object]) -> None:
    assert isinstance(data["code"], str)
    assert isinstance(data["message"], str)
    assert isinstance(data["request_id"], str)
    assert "details" in data


def test_validation_error_uses_unified_response_format() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "password123",
                "full_name": "Invalid Email",
            },
        )

    data = response_dict(response.json())

    assert response.status_code == 422
    assert response.headers[REQUEST_ID_HEADER] == data["request_id"]
    assert data["code"] == "VALIDATION_ERROR"
    assert data["message"] == "Validation failed"
    assert isinstance(data["details"], list)
    assert data["request_id"]


def test_protected_endpoint_without_token_returns_unified_401() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/users/me")

    data = response_dict(response.json())

    assert response.status_code == 401
    assert response.headers[REQUEST_ID_HEADER] == data["request_id"]
    assert data["code"] == "UNAUTHORIZED"
    assert_error_shape(data)


def test_missing_route_returns_unified_404() -> None:
    with TestClient(app) as client:
        response = client.get("/api/v1/not-found")

    data = response_dict(response.json())

    assert response.status_code == 404
    assert response.headers[REQUEST_ID_HEADER] == data["request_id"]
    assert data["code"] == "NOT_FOUND"
    assert data["message"] == "Resource not found"


def test_business_conflict_returns_unified_409() -> None:
    email = f"error-conflict-{uuid4().hex}@example.com"

    with TestClient(app) as client:
        register_user(client, email)
        response = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "password123",
                "full_name": "Duplicate User",
            },
        )

    data = response_dict(response.json())

    assert response.status_code == 409
    assert response.headers[REQUEST_ID_HEADER] == data["request_id"]
    assert data["code"] == "CONFLICT"
    assert_error_shape(data)


def test_custom_request_id_is_returned_in_header_and_error_body() -> None:
    request_id = f"test-request-{uuid4().hex}"

    with TestClient(app) as client:
        response = client.get(
            "/api/v1/users/me",
            headers={REQUEST_ID_HEADER: request_id},
        )

    data = response_dict(response.json())

    assert response.status_code == 401
    assert response.headers[REQUEST_ID_HEADER] == request_id
    assert data["request_id"] == request_id
