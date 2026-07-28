from fastapi import APIRouter
from sqlalchemy import text

from app.core.redis import redis_client
from app.db.session import engine

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))

    await redis_client.ping()

    return {
        "status": "ok",
        "database": "connected",
        "redis": "connected",
    }
