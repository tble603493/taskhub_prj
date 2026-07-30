from datetime import UTC, datetime, timedelta
from typing import Any, cast
from uuid import uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return str(password_context.hash(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(password_context.verify(plain_password, hashed_password))


def create_token_id() -> str:
    return str(uuid4())


def create_access_token(subject: str) -> str:
    now = datetime.now(UTC)
    expire_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": expire_at,
        "jti": create_token_id(),
    }
    return str(
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    )


def create_refresh_token(subject: str) -> str:
    now = datetime.now(UTC)
    expire_at = now + timedelta(days=settings.refresh_token_expire_days)
    payload = {
        "sub": subject,
        "type": "refresh",
        "iat": now,
        "exp": expire_at,
        "jti": create_token_id(),
    }
    return str(
        jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    )


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = cast(
            dict[str, Any],
            jwt.decode(
                token,
                settings.jwt_secret_key,
                algorithms=[settings.jwt_algorithm],
            ),
        )
    except JWTError as e:
        raise ValueError("Invalid token") from e
    return payload
