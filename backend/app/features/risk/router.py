"""M9 风控 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.risk.schema import RiskRuleSetUpsert
from app.features.risk.service import RiskService

router = APIRouter(tags=["Risk"])


@router.get("/risk/rule-sets", summary="风控规则集列表")
async def list_rule_sets(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await RiskService(session).list_rule_sets(principal.user_id, page, size)
    return paginated(items, total, page, size)


@router.post("/risk/rule-sets", summary="创建风控规则集")
async def create_rule_set(
    payload: RiskRuleSetUpsert,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await RiskService(session).create_rule_set(principal.user_id, payload)
    return success(data, message="创建成功")


@router.put("/risk/rule-sets/{id}", summary="更新风控规则集")
async def update_rule_set(
    id: int,
    payload: RiskRuleSetUpsert,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await RiskService(session).update_rule_set(principal.user_id, id, payload)
    return success(data, message="已更新")


@router.delete("/risk/rule-sets/{id}", summary="删除风控规则集")
async def delete_rule_set(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    await RiskService(session).delete_rule_set(principal.user_id, id)
    return success(message="已删除")


@router.get("/risk/events", summary="风控事件")
async def list_risk_events(
    portfolio_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await RiskService(session).list_events(
        principal.user_id, portfolio_id, page, size
    )
    return paginated(items, total, page, size)
