from typing import cast
from uuid import uuid4

from fastapi.testclient import TestClient
from redis import Redis

from app.core.config import settings
from app.main import app
from app.models.enums import TaskPriority, TaskStatus, WorkspaceRole
from app.services.cache import CACHE_PREFIX
from app.services.task_cache import build_task_list_cache_key

redis_client = Redis.from_url(
    settings.redis_url,
    encoding="utf-8",
    decode_responses=True,
)


def unique_email() -> str:
    return f"cache-{uuid4().hex}@example.com"


def response_dict(response_json: object) -> dict[str, object]:
    assert isinstance(response_json, dict)
    return cast(dict[str, object], response_json)


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
            "full_name": "Cache Test User",
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
            "description": "Cache test workspace",
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
            "description": "Cache test project",
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


def create_task(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    *,
    title: str | None = None,
    priority: TaskPriority = TaskPriority.MEDIUM,
    assignee_id: int | None = None,
) -> dict[str, object]:
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        json={
            "title": title or f"Task {uuid4().hex}",
            "description": "Cache test task",
            "priority": priority,
            "assignee_id": assignee_id,
        },
    )
    assert response.status_code == 201
    return response_dict(response.json())


def setup_project(
    client: TestClient,
) -> tuple[dict[str, str], int, int, int, int]:
    _, owner_headers, owner_id = register_and_login(client)
    workspace_id = object_id(create_workspace(client, owner_headers))
    project_id = object_id(create_project(client, owner_headers, workspace_id))

    member_email, _, member_id = register_and_login(client)
    add_member(
        client,
        owner_headers,
        workspace_id,
        member_email,
        WorkspaceRole.EDITOR,
    )

    return owner_headers, owner_id, member_id, workspace_id, project_id


def redis_task_list_key(
    *,
    workspace_id: int,
    project_id: int,
    page: int = 1,
    limit: int = 20,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
) -> str:
    return (
        CACHE_PREFIX
        + build_task_list_cache_key(
            workspace_id=workspace_id,
            project_id=project_id,
            page=page,
            limit=limit,
            status=status,
            priority=priority,
            assignee_id=assignee_id,
        )
    )


def delete_project_cache_keys(workspace_id: int, project_id: int) -> None:
    pattern = (
        f"{CACHE_PREFIX}tasks:list:workspace:{workspace_id}:project:{project_id}:*"
    )
    for key in redis_client.scan_iter(match=pattern):
        redis_client.delete(key)


def redis_key_exists(key: str) -> bool:
    return bool(redis_client.exists(key))


def list_tasks(
    client: TestClient,
    headers: dict[str, str],
    workspace_id: int,
    project_id: int,
    params: dict[str, object] | None = None,
) -> dict[str, object]:
    response = client.get(
        f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks",
        headers=headers,
        params=params or {},
    )
    assert response.status_code == 200
    return response_dict(response.json())


def test_task_list_cache_key_contains_project_filters_and_pagination() -> None:
    key = build_task_list_cache_key(
        workspace_id=1,
        project_id=2,
        status=TaskStatus.TODO,
        priority=TaskPriority.HIGH,
        assignee_id=3,
        page=4,
        limit=50,
    )

    assert key == (
        "tasks:list:workspace:1:project:2:"
        "status:TODO:priority:HIGH:assignee:3:page:4:limit:50"
    )


def test_first_task_list_call_creates_cache_key() -> None:
    with TestClient(app) as client:
        headers, _, _, workspace_id, project_id = setup_project(client)
        create_task(client, headers, workspace_id, project_id)
        delete_project_cache_keys(workspace_id, project_id)

        list_tasks(client, headers, workspace_id, project_id)

        key = redis_task_list_key(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        exists = redis_key_exists(key)

    assert exists


def test_second_task_list_call_uses_cached_response() -> None:
    with TestClient(app) as client:
        headers, _, _, workspace_id, project_id = setup_project(client)
        create_task(client, headers, workspace_id, project_id, title="Cached Task")
        delete_project_cache_keys(workspace_id, project_id)

        first_response = list_tasks(client, headers, workspace_id, project_id)
        key = redis_task_list_key(
            workspace_id=workspace_id,
            project_id=project_id,
        )
        redis_client.delete(key)
        redis_client.set(
            key,
            '{"items":[],"total":123,"page":1,"limit":20,"pages":7}',
            ex=60,
        )
        second_response = list_tasks(client, headers, workspace_id, project_id)

    assert first_response["total"] == 1
    assert second_response["total"] == 123
    assert second_response["items"] == []


def test_task_list_filter_and_pagination_create_distinct_cache_keys() -> None:
    with TestClient(app) as client:
        headers, owner_id, member_id, workspace_id, project_id = setup_project(client)
        create_task(
            client,
            headers,
            workspace_id,
            project_id,
            priority=TaskPriority.HIGH,
            assignee_id=owner_id,
        )
        create_task(
            client,
            headers,
            workspace_id,
            project_id,
            priority=TaskPriority.LOW,
            assignee_id=member_id,
        )
        delete_project_cache_keys(workspace_id, project_id)

        list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"status": TaskStatus.TODO},
        )
        list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"priority": TaskPriority.HIGH},
        )
        list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"assignee_id": member_id},
        )
        list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"page": 1, "limit": 1},
        )
        list_tasks(
            client,
            headers,
            workspace_id,
            project_id,
            {"page": 2, "limit": 1},
        )

        keys = [
            redis_task_list_key(
                workspace_id=workspace_id,
                project_id=project_id,
                status=TaskStatus.TODO,
            ),
            redis_task_list_key(
                workspace_id=workspace_id,
                project_id=project_id,
                priority=TaskPriority.HIGH,
            ),
            redis_task_list_key(
                workspace_id=workspace_id,
                project_id=project_id,
                assignee_id=member_id,
            ),
            redis_task_list_key(
                workspace_id=workspace_id,
                project_id=project_id,
                page=1,
                limit=1,
            ),
            redis_task_list_key(
                workspace_id=workspace_id,
                project_id=project_id,
                page=2,
                limit=1,
            ),
        ]
        existing = [redis_key_exists(key) for key in keys]

    assert existing == [True, True, True, True, True]
    assert len(set(keys)) == len(keys)


def test_create_task_invalidates_task_list_cache() -> None:
    with TestClient(app) as client:
        headers, _, _, workspace_id, project_id = setup_project(client)
        delete_project_cache_keys(workspace_id, project_id)
        list_tasks(client, headers, workspace_id, project_id)
        key = redis_task_list_key(workspace_id=workspace_id, project_id=project_id)
        assert redis_key_exists(key)

        create_task(client, headers, workspace_id, project_id)
        exists = redis_key_exists(key)

    assert not exists


def test_update_task_invalidates_task_list_cache() -> None:
    with TestClient(app) as client:
        headers, _, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        delete_project_cache_keys(workspace_id, project_id)
        list_tasks(client, headers, workspace_id, project_id)
        key = redis_task_list_key(workspace_id=workspace_id, project_id=project_id)
        assert redis_key_exists(key)

        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"title": "Updated cached task"},
        )
        exists = redis_key_exists(key)

    assert response.status_code == 200
    assert not exists


def test_delete_task_invalidates_task_list_cache() -> None:
    with TestClient(app) as client:
        headers, _, _, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        delete_project_cache_keys(workspace_id, project_id)
        list_tasks(client, headers, workspace_id, project_id)
        key = redis_task_list_key(workspace_id=workspace_id, project_id=project_id)
        assert redis_key_exists(key)

        response = client.delete(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
        )
        exists = redis_key_exists(key)

    assert response.status_code == 204
    assert not exists


def test_assign_task_invalidates_task_list_cache() -> None:
    with TestClient(app) as client:
        headers, _, member_id, workspace_id, project_id = setup_project(client)
        task = create_task(client, headers, workspace_id, project_id)
        delete_project_cache_keys(workspace_id, project_id)
        list_tasks(client, headers, workspace_id, project_id)
        key = redis_task_list_key(workspace_id=workspace_id, project_id=project_id)
        assert redis_key_exists(key)

        response = client.patch(
            f"/api/v1/workspaces/{workspace_id}/projects/{project_id}/tasks/{task['id']}",
            headers=headers,
            json={"assignee_id": member_id},
        )
        exists = redis_key_exists(key)

    assert response.status_code == 200
    assert not exists
