"""M7 组合 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.portfolios.schema import PortfolioUpsert
from app.features.portfolios.service import PortfolioService

router = APIRouter(tags=["Portfolios"])


@router.get("/portfolios", summary="组合列表")
async def list_portfolios(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await PortfolioService(session).list_portfolios(
        principal.user_id, page, size
    )
    return paginated(items, total, page, size)


@router.post("/portfolios", summary="创建组合")
async def create_portfolio(
    payload: PortfolioUpsert,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await PortfolioService(session).create_portfolio(principal.user_id, payload)
    return success(data, message="创建成功")


@router.get("/portfolios/{id}", summary="组合详情")
async def get_portfolio(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await PortfolioService(session).get_portfolio(principal.user_id, id)
    return success(data)


@router.delete("/portfolios/{id}", summary="删除组合")
async def delete_portfolio(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    await PortfolioService(session).delete_portfolio(principal.user_id, id)
    return success(message="已删除")


@router.get("/portfolios/{id}/positions", summary="当前持仓")
async def list_positions(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items = await PortfolioService(session).list_positions(principal.user_id, id)
    return success(items)


@router.post("/portfolios/{id}/rebalance", summary="触发再平衡")
async def rebalance_portfolio(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await PortfolioService(session).rebalance(principal.user_id, id)
    return success(data, message="再平衡完成")
