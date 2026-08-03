from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.comments import router as comments_router
from app.api.v1.health import router as health_router
from app.api.v1.labels import router as labels_router
from app.api.v1.projects import router as projects_router
from app.api.v1.tasks import router as tasks_router
from app.api.v1.users import router as users_router
from app.api.v1.workspaces import router as workspaces_router

api_router = APIRouter()

api_router.include_router(auth_router, prefix="/auth")
api_router.include_router(health_router)
api_router.include_router(users_router, prefix="/users")
api_router.include_router(workspaces_router, prefix="/workspaces")
api_router.include_router(projects_router)
api_router.include_router(tasks_router)
api_router.include_router(labels_router)
api_router.include_router(comments_router)
