"""M9 风控数据访问。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.features.risk.models import RiskEvent, RiskRule, RiskRuleSet


class RiskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_rule_sets(self, user_id: int, page: int, size: int) -> tuple[list[RiskRuleSet], int]:
        base = (
            select(RiskRuleSet)
            .where(RiskRuleSet.user_id == user_id)
            .options(selectinload(RiskRuleSet.rules))
            .order_by(RiskRuleSet.id.desc())
        )
        total = (
            await self._session.execute(select(func.count()).select_from(base.subquery()))
        ).scalar_one()
        rows = (
            await self._session.execute(base.offset((page - 1) * size).limit(size))
        ).scalars().all()
        return list(rows), int(total)

    async def get_rule_set(self, rule_set_id: int, user_id: int) -> Optional[RiskRuleSet]:
        return (
            await self._session.execute(
                select(RiskRuleSet)
                .where(RiskRuleSet.id == rule_set_id, RiskRuleSet.user_id == user_id)
                .options(selectinload(RiskRuleSet.rules))
            )
        ).scalar_one_or_none()

    async def add_rule_set(self, rs: RiskRuleSet) -> RiskRuleSet:
        self._session.add(rs)
        await self._session.flush()
        return rs

    async def delete_rule_set(self, rs: RiskRuleSet) -> None:
        await self._session.delete(rs)

    async def replace_rules(self, rule_set_id: int, rules: list[RiskRule]) -> None:
        existing = (
            await self._session.execute(select(RiskRule).where(RiskRule.rule_set_id == rule_set_id))
        ).scalars().all()
        for r in existing:
            await self._session.delete(r)
        for r in rules:
            self._session.add(r)
        await self._session.flush()

    async def list_events(
        self, user_id: int, portfolio_id: Optional[int], page: int, size: int
    ) -> tuple[list[RiskEvent], int]:
        stmt = select(RiskEvent).where(RiskEvent.user_id == user_id)
        if portfolio_id is not None:
            stmt = stmt.where(RiskEvent.portfolio_id == portfolio_id)
        stmt = stmt.order_by(RiskEvent.id.desc())
        rows = (await self._session.execute(stmt)).scalars().all()
        total = len(rows)
        start = (page - 1) * size
        return list(rows[start : start + size]), total

    async def add_event(self, event: RiskEvent) -> RiskEvent:
        self._session.add(event)
        await self._session.flush()
        return event
