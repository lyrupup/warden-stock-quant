"""M3 策略管理 API。"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.strategies.schema import StrategyUpsert, StrategyValidateRequest
from app.features.strategies.service import StrategyService

router = APIRouter(tags=["Strategies"])


@router.get("/strategies", summary="策略列表")
async def list_strategies(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await StrategyService(session).list_strategies(
        principal.user_id, page, size
    )
    return paginated(items, total, page, size)


@router.post("/strategies", summary="创建策略")
async def create_strategy(
    payload: StrategyUpsert,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await StrategyService(session).create_strategy(principal.user_id, payload)
    return success(data, message="创建成功")


@router.get("/strategies/{id}", summary="策略详情")
async def get_strategy(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await StrategyService(session).get_strategy(principal.user_id, id)
    return success(data)


@router.put("/strategies/{id}", summary="更新策略（生成新版本）")
async def update_strategy(
    payload: StrategyUpsert,
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await StrategyService(session).update_strategy(principal.user_id, id, payload)
    return success(data, message="已保存新版本")


@router.delete("/strategies/{id}", summary="删除策略")
async def delete_strategy(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    await StrategyService(session).delete_strategy(principal.user_id, id)
    return success(message="已删除")


@router.get("/strategies/{id}/versions", summary="版本列表")
async def list_versions(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items = await StrategyService(session).list_versions(principal.user_id, id)
    return success(items)


@router.post("/strategies/{id}/validate", summary="校验策略配置")
async def validate_strategy(
    id: int,
    payload: Optional[StrategyValidateRequest] = None,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await StrategyService(session).validate_strategy(
        principal.user_id, id, payload
    )
    return success(data)


@router.get("/strategy-templates", summary="策略模板库")
async def list_strategy_templates(
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items = await StrategyService(session).list_templates()
    return success(items)
