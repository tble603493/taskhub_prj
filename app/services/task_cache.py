import logging

from app.models.enums import TaskPriority, TaskStatus
from app.services.cache import CacheService

TASK_LIST_CACHE_KEY_PREFIX = "tasks:list"

logger = logging.getLogger(__name__)


def _enum_value(value: TaskStatus | TaskPriority | None) -> str:
    if value is None:
        return "all"

    return value.value


def _nullable_int_value(value: int | None) -> str:
    if value is None:
        return "all"

    return str(value)


def build_task_list_cache_key(
    *,
    workspace_id: int,
    project_id: int,
    page: int,
    limit: int,
    status: TaskStatus | None = None,
    priority: TaskPriority | None = None,
    assignee_id: int | None = None,
) -> str:
    return (
        f"{TASK_LIST_CACHE_KEY_PREFIX}:"
        f"workspace:{workspace_id}:"
        f"project:{project_id}:"
        f"status:{_enum_value(status)}:"
        f"priority:{_enum_value(priority)}:"
        f"assignee:{_nullable_int_value(assignee_id)}:"
        f"page:{page}:"
        f"limit:{limit}"
    )


def build_task_list_cache_pattern(
    *,
    workspace_id: int,
    project_id: int,
) -> str:
    return (
        f"{TASK_LIST_CACHE_KEY_PREFIX}:workspace:{workspace_id}:project:{project_id}:*"
    )


async def invalidate_task_list_cache(
    *,
    cache_service: CacheService,
    workspace_id: int,
    project_id: int,
) -> None:
    pattern = build_task_list_cache_pattern(
        workspace_id=workspace_id,
        project_id=project_id,
    )

    try:
        await cache_service.delete_pattern(pattern)
    except Exception:
        logger.warning(
            "Failed to invalidate task list cache",
            exc_info=True,
            extra={
                "workspace_id": workspace_id,
                "project_id": project_id,
            },
        )
