from uuid import uuid4

from starlette.requests import Request

REQUEST_ID_HEADER = "X-Request-ID"


def create_request_id() -> str:
    return str(uuid4())


def get_request_id(request: Request) -> str | None:
    request_id = getattr(request.state, "request_id", None)
    if isinstance(request_id, str):
        return request_id
    return None


def get_or_create_request_id(request: Request) -> str:
    request_id = request.headers.get(REQUEST_ID_HEADER)
    if request_id:
        return request_id
    return create_request_id()
