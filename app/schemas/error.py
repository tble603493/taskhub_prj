from typing import Any

from pydantic import BaseModel


class ValidationErrorItem(BaseModel):
    field: str
    message: str


class ErrorResponse(BaseModel):
    code: str
    message: str
    details: list[ValidationErrorItem | dict[str, Any]] | None = None
    request_id: str | None = None
