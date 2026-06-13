"""M9 风控业务编排。"""

from __future__ import annotations

from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine.risk import RiskEngine, RiskRuleDef
from app.core.errors import NotFoundError
from app.features.risk.models import RiskRule, RiskRuleSet, RiskEvent
from app.features.risk.repository import RiskRepository
from app.features.risk.schema import RiskEventView, RiskRuleSetUpsert, RiskRuleSetView


DEFAULT_RULES = [
    RiskRuleDef(type="tradable", action="reject"),
    RiskRuleDef(type="no_st", action="reject"),
    RiskRuleDef(type="max_order_amount", params={"max": 500000}, action="reject"),
]


class RiskService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RiskRepository(session)

    def _to_view(self, rs: RiskRuleSet) -> dict:
        return RiskRuleSetView(
            id=rs.id,
            name=rs.name,
            scope=rs.scope,
            is_platform=rs.is_platform,
            rules=[
                {
                    "type": r.type,
                    "params": r.params,
                    "action": r.action,
                    "enabled": r.enabled,
                }
                for r in rs.rules
            ],
            created_at=rs.created_at,
        ).model_dump()

    async def list_rule_sets(self, user_id: int, page: int, size: int) -> tuple[list[dict], int]:
        rows, total = await self._repo.list_rule_sets(user_id, page, size)
        return [self._to_view(r) for r in rows], total

    async def create_rule_set(self, user_id: int, payload: RiskRuleSetUpsert) -> dict:
        rs = RiskRuleSet(user_id=user_id, name=payload.name, scope=payload.scope)
        await self._repo.add_rule_set(rs)
        rules = [
            RiskRule(
                rule_set_id=rs.id,
                type=item.type,
                params=item.params,
                action=item.action,
                enabled=item.enabled,
            )
            for item in payload.rules
        ]
        await self._repo.replace_rules(rs.id, rules)
        rs = await self._repo.get_rule_set(rs.id, user_id)
        assert rs is not None
        return self._to_view(rs)

    async def update_rule_set(
        self, user_id: int, rule_set_id: int, payload: RiskRuleSetUpsert
    ) -> dict:
        rs = await self._require_rule_set(rule_set_id, user_id)
        rs.name = payload.name
        rs.scope = payload.scope
        rules = [
            RiskRule(
                rule_set_id=rs.id,
                type=item.type,
                params=item.params,
                action=item.action,
                enabled=item.enabled,
            )
            for item in payload.rules
        ]
        await self._repo.replace_rules(rs.id, rules)
        await self._session.flush()
        rs = await self._repo.get_rule_set(rs.id, user_id)
        assert rs is not None
        return self._to_view(rs)

    async def delete_rule_set(self, user_id: int, rule_set_id: int) -> None:
        rs = await self._require_rule_set(rule_set_id, user_id)
        await self._repo.delete_rule_set(rs)

    async def list_events(
        self, user_id: int, portfolio_id: Optional[int], page: int, size: int
    ) -> tuple[list[dict], int]:
        rows, total = await self._repo.list_events(user_id, portfolio_id, page, size)
        items = [RiskEventView.model_validate(r, from_attributes=True).model_dump() for r in rows]
        return items, total

    async def load_engine_for_portfolio(
        self, user_id: int, portfolio_rule_set_id: Optional[int]
    ) -> RiskEngine:
        rules: list[RiskRuleDef] = list(DEFAULT_RULES)
        if portfolio_rule_set_id:
            rs = await self._repo.get_rule_set(portfolio_rule_set_id, user_id)
            if rs:
                rules = [
                    RiskRuleDef(
                        type=r.type,
                        params=r.params or {},
                        action=r.action,
                        enabled=r.enabled,
                    )
                    for r in rs.rules
                ] + rules
        return RiskEngine(rules)

    async def record_rejection(
        self,
        user_id: int,
        portfolio_id: int,
        order_id: Optional[int],
        rule_type: str,
        action: str,
        reason: str,
    ) -> None:
        await self._repo.add_event(
            RiskEvent(
                user_id=user_id,
                portfolio_id=portfolio_id,
                order_id=order_id,
                rule_type=rule_type,
                action=action,
                detail={"reason": reason},
            )
        )

    async def _require_rule_set(self, rule_set_id: int, user_id: int) -> RiskRuleSet:
        rs = await self._repo.get_rule_set(rule_set_id, user_id)
        if rs is None:
            raise NotFoundError("风控规则集不存在")
        return rs
