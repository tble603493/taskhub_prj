import json
from typing import Any

from redis.asyncio import Redis

from app.core.redis import redis_client

CACHE_PREFIX = "taskhub:cache:"


class CacheService:
    def __init__(self, redis: Redis = redis_client) -> None:
        self.redis = redis

    def build_key(self, key: str) -> str:
        if key.startswith(CACHE_PREFIX):
            return key

        return f"{CACHE_PREFIX}{key}"

    async def get_json(self, key: str) -> dict[str, Any] | list[Any] | None:
        cache_key = self.build_key(key)

        raw_value = await self.redis.get(cache_key)

        if raw_value is None:
            return None

        value = json.loads(raw_value)

        if isinstance(value, dict | list):
            return value

        return None

    async def set_json(
        self,
        key: str,
        value: dict[str, Any] | list[Any],
        ttl_seconds: int,
    ) -> None:
        cache_key = self.build_key(key)

        serialized_value = json.dumps(value)

        await self.redis.set(
            cache_key,
            serialized_value,
            ex=ttl_seconds,
        )

    async def delete(self, key: str) -> None:
        cache_key = self.build_key(key)

        await self.redis.delete(cache_key)

    async def delete_pattern(self, pattern: str) -> None:
        cache_pattern = self.build_key(pattern)

        async for key in self.redis.scan_iter(match=cache_pattern):
            await self.redis.delete(key)
