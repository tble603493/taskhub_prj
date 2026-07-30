from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_client
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserCreate
from app.services.user import UserService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repository = UserRepository(session)
        self.user_service = UserService(session)

    async def register(self, data: RegisterRequest) -> User:
        return await self.user_service.create_user(
            UserCreate(
                email=data.email,
                password=data.password,
                full_name=data.full_name,
            )
        )

    async def authenticate(self, email: str, password: str) -> User:
        user = await self.user_repository.get_by_email(email)

        if user is None or not verify_password(password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )

        return user

    async def login(self, data: LoginRequest) -> TokenResponse:
        user = await self.authenticate(str(data.email), data.password)

        return self._create_token_response(user)

    async def refresh(self, refresh_token: str) -> TokenResponse:
        payload = self._decode_token(refresh_token)
        self._require_token_type(payload, "refresh")

        token_id = self._get_required_claim(payload, "jti")

        if await self._is_refresh_token_revoked(token_id):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token has been revoked",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = int(self._get_required_claim(payload, "sub"))
        user = await self.user_service.get_user(user_id)

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is inactive",
            )

        return self._create_token_response(user)

    async def logout(self, refresh_token: str) -> None:
        payload = self._decode_token(refresh_token)
        self._require_token_type(payload, "refresh")

        token_id = self._get_required_claim(payload, "jti")
        user_id = self._get_required_claim(payload, "sub")
        ttl = self._get_token_ttl_seconds(payload)

        if ttl > 0:
            await redis_client.set(
                self._revoked_refresh_key(token_id),
                user_id,
                ex=ttl,
            )

    def _create_token_response(self, user: User) -> TokenResponse:
        subject = str(user.id)

        return TokenResponse(
            access_token=create_access_token(subject),
            refresh_token=create_refresh_token(subject),
        )

    def _decode_token(self, token: str) -> dict[str, Any]:
        try:
            return decode_token(token)
        except ValueError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            ) from error

    def _require_token_type(self, payload: dict[str, Any], token_type: str) -> None:
        if payload.get("type") != token_type:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token type. Expected {token_type}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    def _get_required_claim(self, payload: dict[str, Any], claim: str) -> str:
        value = payload.get(claim)

        if value is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return str(value)

    def _get_token_ttl_seconds(self, payload: dict[str, Any]) -> int:
        expires_at = payload.get("exp")

        if not isinstance(expires_at, int):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token expiration",
                headers={"WWW-Authenticate": "Bearer"},
            )

        now = int(datetime.now(UTC).timestamp())

        return expires_at - now

    async def _is_refresh_token_revoked(self, token_id: str) -> bool:
        return await redis_client.exists(self._revoked_refresh_key(token_id)) > 0

    def _revoked_refresh_key(self, token_id: str) -> str:
        return f"taskhub:revoked_refresh:{token_id}"
