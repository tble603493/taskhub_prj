import logging
from collections.abc import Mapping, Sequence
from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import REQUEST_ID_HEADER, get_request_id
from app.schemas.error import ErrorResponse, ValidationErrorItem

logger = logging.getLogger(__name__)


ERROR_CODE_BY_STATUS = {
    status.HTTP_400_BAD_REQUEST: "BAD_REQUEST",
    status.HTTP_401_UNAUTHORIZED: "UNAUTHORIZED",
    status.HTTP_403_FORBIDDEN: "FORBIDDEN",
    status.HTTP_404_NOT_FOUND: "NOT_FOUND",
    status.HTTP_409_CONFLICT: "CONFLICT",
    422: "VALIDATION_ERROR",
}


def _request_id_headers(request_id: str | None) -> dict[str, str]:
    if request_id is None:
        return {}
    return {REQUEST_ID_HEADER: request_id}


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    request_id: str | None,
    details: Sequence[ValidationErrorItem | dict[str, Any]] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    response_headers = _request_id_headers(request_id)
    if headers:
        response_headers.update(headers)

    content = ErrorResponse(
        code=code,
        message=message,
        details=list(details) if details is not None else None,
        request_id=request_id,
    ).model_dump(mode="json")

    return JSONResponse(
        status_code=status_code,
        content=content,
        headers=response_headers,
    )


def _status_code_to_error_code(status_code: int) -> str:
    return ERROR_CODE_BY_STATUS.get(status_code, "HTTP_ERROR")


def _detail_to_message(detail: Any, fallback: str) -> str:
    if isinstance(detail, str):
        return detail
    return fallback


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    request_id = get_request_id(request)
    details = [
        ValidationErrorItem(
            field=".".join(str(part) for part in error["loc"]),
            message=str(error["msg"]),
        )
        for error in exc.errors()
    ]

    return _error_response(
        status_code=422,
        code="VALIDATION_ERROR",
        message="Validation failed",
        details=details,
        request_id=request_id,
    )


async def http_exception_handler(
    request: Request,
    exc: HTTPException,
) -> JSONResponse:
    request_id = get_request_id(request)
    message = _detail_to_message(exc.detail, "HTTP error")

    return _error_response(
        status_code=exc.status_code,
        code=_status_code_to_error_code(exc.status_code),
        message=message,
        request_id=request_id,
        headers=exc.headers,
    )


async def starlette_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
) -> JSONResponse:
    request_id = get_request_id(request)
    message = "Resource not found" if exc.status_code == 404 else str(exc.detail)

    return _error_response(
        status_code=exc.status_code,
        code=_status_code_to_error_code(exc.status_code),
        message=message,
        request_id=request_id,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    request_id = get_request_id(request)
    logger.exception(
        "Unhandled application error",
        extra={"request_id": request_id},
        exc_info=exc,
    )

    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="INTERNAL_SERVER_ERROR",
        message="Internal server error",
        request_id=request_id,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(
        RequestValidationError,
        cast(Any, validation_exception_handler),
    )
    app.add_exception_handler(HTTPException, cast(Any, http_exception_handler))
    app.add_exception_handler(
        StarletteHTTPException,
        cast(Any, starlette_http_exception_handler),
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)
