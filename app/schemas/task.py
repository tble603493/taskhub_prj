from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TaskPriority, TaskStatus


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    priority: TaskPriority = TaskPriority.MEDIUM
    due_date: datetime | None = None
    assignee_id: int | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: datetime | None = None
    assignee_id: int | None = None


class TaskResponse(BaseModel):
    id: int
    project_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: datetime | None
    created_by_id: int
    assignee_id: int | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)