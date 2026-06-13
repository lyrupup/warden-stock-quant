"""用户与 API Key 业务编排。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ForbiddenError, NotFoundError, ValidationFailedError
from app.core.errors.codes import ErrorCode
from app.core.security.api_key import generate_api_key, hash_api_secret
from app.features.users.models import ApiKey, User
from app.features.users.repository import ApiKeyRepository, UserRepository
from app.features.users.schema import (
    ApiKeyCreate,
    ApiKeyCreated,
    ApiKeyView,
    MeResponse,
)

ALLOWED_SCOPES = {"read", "backtest", "factor", "trade"}


class UserService:
    """用户资料与 API Key 管理。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._api_keys = ApiKeyRepository(session)

    async def get_me(self, user_id: int) -> MeResponse:
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise NotFoundError("用户不存在")
        quota = await self._users.ensure_quota(user_id)
        return MeResponse(
            id=user.id,
            email=user.email,
            username=user.username,
            role=user.role,
            plan=user.plan,
            live_enabled=user.live_enabled,
            quota=dict(quota.usage or {}),
        )

    async def create_api_key(self, user_id: int, payload: ApiKeyCreate) -> ApiKeyCreated:
        scopes = payload.scopes or ["read"]
        invalid = [s for s in scopes if s not in ALLOWED_SCOPES]
        if invalid:
            raise ValidationFailedError(f"非法的作用域: {', '.join(invalid)}")

        parts = generate_api_key()
        api_key = ApiKey(
            user_id=user_id,
            name=payload.name,
            prefix=parts.prefix,
            key_hash=hash_api_secret(parts.secret),
            scopes=",".join(scopes),
            status="active",
        )
        await self._api_keys.add(api_key)
        return ApiKeyCreated(
            id=api_key.id,
            name=api_key.name,
            prefix=api_key.prefix,
            scopes=scopes,
            key=parts.full_key,
        )

    async def list_api_keys(self, user_id: int) -> List[ApiKeyView]:
        keys: Sequence[ApiKey] = await self._api_keys.list_by_user(user_id)
        return [self._to_view(k) for k in keys]

    async def revoke_api_key(self, user_id: int, key_id: int) -> None:
        owned = await self._api_keys.get_owned(key_id, user_id)
        if owned is None:
            # 区分「不存在」与「越权」：他人资源返回 403。
            exists = await self._api_keys.get_by_id_any_tenant(key_id)
            if exists is None:
                raise NotFoundError("API Key 不存在")
            raise ForbiddenError("越权访问", code=ErrorCode.FORBIDDEN_TENANT)
        owned.status = "revoked"
        await self._session.flush()

    @staticmethod
    def _to_view(key: ApiKey) -> ApiKeyView:
        scopes = [s for s in (key.scopes or "").replace(",", " ").split() if s]
        return ApiKeyView(
            id=key.id,
            name=key.name,
            prefix=key.prefix,
            scopes=scopes,
            status=key.status,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
        )

    @staticmethod
    def to_user_summary(user: User) -> dict:
        return {
            "id": user.id,
            "email": user.email,
            "username": user.username,
            "role": user.role,
            "plan": user.plan,
        }
