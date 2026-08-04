from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TaskHub"

    app_env: Literal["development", "testing", "production"] = "development"

    debug: bool = False

    api_v1_prefix: str = "/api/v1"

    database_url: str = Field(min_length=1)

    redis_url: str = Field(min_length=1)

    jwt_secret_key: str = Field(min_length=1)

    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = Field(default=15, gt=0)

    refresh_token_expire_days: int = Field(default=7, gt=0)

    task_list_cache_ttl_seconds: int = Field(default=60, gt=0)

    notification_enabled: bool = True

    notification_from_email: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings = get_settings()
