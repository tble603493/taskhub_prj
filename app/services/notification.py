import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(self, enabled: bool = settings.notification_enabled) -> None:
        self.enabled = enabled

    def notify_task_assigned(
        self,
        task_id: int,
        assignee_id: int,
    ) -> None:
        if not self.enabled:
            logger.info(
                "Task assignment notification skipped because notification is disabled",
                extra={
                    "task_id": task_id,
                    "assignee_id": assignee_id,
                },
            )
            return

        try:
            logger.info(
                "Task assigned notification: Task %s assigned to user %s",
                task_id,
                assignee_id,
                extra={
                    "task_id": task_id,
                    "assignee_id": assignee_id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to send task assigned notification",
                exc_info=True,
                extra={
                    "task_id": task_id,
                    "assignee_id": assignee_id,
                },
            )


def notify_task_assigned_safely(task_id: int, assignee_id: int) -> None:
    try:
        NotificationService().notify_task_assigned(
            task_id=task_id,
            assignee_id=assignee_id,
        )
    except Exception:
        logger.warning(
            "Task assignment background notification failed",
            exc_info=True,
            extra={
                "task_id": task_id,
                "assignee_id": assignee_id,
            },
        )
