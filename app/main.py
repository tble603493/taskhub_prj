from fastapi import FastAPI

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.middleware.access_log import AccessLogMiddleware
from app.middleware.request_id import RequestIDMiddleware

configure_logging()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    version="0.1.0",
    description=(
        "TaskHub API for workspaces, projects, tasks, labels, comments, "
        "JWT authentication, RBAC, Redis cache and assignment notifications."
    ),
    lifespan=lifespan,
)

app.add_middleware(AccessLogMiddleware)
app.add_middleware(RequestIDMiddleware)
register_exception_handlers(app)


@app.get(
    "/",
    tags=["Root"],
    summary="API welcome",
    description="Return a simple welcome message for the TaskHub API.",
)
async def root() -> dict[str, str]:
    return {
        "message": "Welcome to TaskHub API",
    }


app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)
