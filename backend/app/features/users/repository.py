"""用户与 API Key 数据访问层（仅此层接触 ORM）。

所有按租户的查询均强制注入 user_id 作用域。
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.users.models import ApiKey, Quota, User


class UserRepository:
    """用户数据访问。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> Optional[User]:
        return (
            await self._session.execute(select(User).where(User.id == user_id))
        ).scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        return (
            await self._session.execute(select(User).where(User.email == email))
        ).scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        return (
            await self._session.execute(
                select(User).where(User.username == username)
            )
        ).scalar_one_or_none()

    async def get_by_account(self, account: str) -> Optional[User]:
        """按邮箱或用户名查找。"""
        return (
            await self._session.execute(
                select(User).where(
                    (User.email == account) | (User.username == account)
                )
            )
        ).scalar_one_or_none()

    async def add(self, user: User) -> User:
        self._session.add(user)
        await self._session.flush()
        return user

    async def ensure_quota(self, user_id: int) -> Quota:
        quota = (
            await self._session.execute(
                select(Quota).where(Quota.user_id == user_id)
            )
        ).scalar_one_or_none()
        if quota is None:
            quota = Quota(user_id=user_id, usage={})
            self._session.add(quota)
            await self._session.flush()
        return quota


class ApiKeyRepository:
    """API Key 数据访问（按租户作用域）。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, api_key: ApiKey) -> ApiKey:
        self._session.add(api_key)
        await self._session.flush()
        return api_key

    async def list_by_user(self, user_id: int) -> Sequence[ApiKey]:
        result = await self._session.execute(
            select(ApiKey)
            .where(ApiKey.user_id == user_id)
            .order_by(ApiKey.created_at.desc())
        )
        return result.scalars().all()

    async def count_by_user(self, user_id: int) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(ApiKey)
                    .where(ApiKey.user_id == user_id)
                )
            ).scalar_one()
        )

    async def get_owned(self, key_id: int, user_id: int) -> Optional[ApiKey]:
        """按 id 取本租户的 key；不存在返回 None。"""
        return (
            await self._session.execute(
                select(ApiKey).where(
                    ApiKey.id == key_id, ApiKey.user_id == user_id
                )
            )
        ).scalar_one_or_none()

    async def get_by_id_any_tenant(self, key_id: int) -> Optional[ApiKey]:
        """不带租户作用域取 key（用于区分 404 与越权 403）。"""
        return (
            await self._session.execute(select(ApiKey).where(ApiKey.id == key_id))
        ).scalar_one_or_none()

    async def get_by_prefix(self, prefix: str) -> Optional[ApiKey]:
        return (
            await self._session.execute(
                select(ApiKey).where(ApiKey.prefix == prefix)
            )
        ).scalar_one_or_none()


__all__: List[str] = ["UserRepository", "ApiKeyRepository"]
