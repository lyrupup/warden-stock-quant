"""M3 策略数据访问层（强制租户作用域）。"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.strategies.models import Strategy, StrategyVersion


class StrategyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, strategy: Strategy) -> Strategy:
        self._session.add(strategy)
        await self._session.flush()
        return strategy

    async def add_version(self, version: StrategyVersion) -> StrategyVersion:
        self._session.add(version)
        await self._session.flush()
        return version

    async def list_by_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[Sequence[Strategy], int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(Strategy)
                    .where(Strategy.user_id == user_id)
                )
            ).scalar_one()
        )
        offset = max(page - 1, 0) * size
        rows = (
            await self._session.execute(
                select(Strategy)
                .where(Strategy.user_id == user_id)
                .order_by(Strategy.updated_at.desc())
                .offset(offset)
                .limit(size)
            )
        ).scalars().all()
        return rows, total

    async def get_owned(self, strategy_id: int, user_id: int) -> Optional[Strategy]:
        return (
            await self._session.execute(
                select(Strategy)
                .options(selectinload(Strategy.versions))
                .where(Strategy.id == strategy_id, Strategy.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def get_by_id_any_tenant(self, strategy_id: int) -> Optional[Strategy]:
        return (
            await self._session.execute(select(Strategy).where(Strategy.id == strategy_id))
        ).scalar_one_or_none()

    async def get_by_name(self, user_id: int, name: str) -> Optional[Strategy]:
        return (
            await self._session.execute(
                select(Strategy).where(Strategy.user_id == user_id, Strategy.name == name)
            )
        ).scalar_one_or_none()

    async def list_versions(self, strategy_id: int) -> Sequence[StrategyVersion]:
        result = await self._session.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version.desc())
        )
        return result.scalars().all()

    async def get_latest_version(self, strategy_id: int) -> Optional[StrategyVersion]:
        return (
            await self._session.execute(
                select(StrategyVersion)
                .where(StrategyVersion.strategy_id == strategy_id)
                .order_by(StrategyVersion.version.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    async def delete(self, strategy: Strategy) -> None:
        await self._session.delete(strategy)
        await self._session.flush()
