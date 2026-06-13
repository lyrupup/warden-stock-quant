"""M4 回测 API。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import job_accepted, paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.backtests.schema import BacktestCreate
from app.features.backtests.service import BacktestService

router = APIRouter(tags=["Backtests"])


@router.get("/backtests", summary="回测列表")
async def list_backtests(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await BacktestService(session).list_backtests(
        principal.user_id, page, size
    )
    return paginated([i.model_dump() for i in items], total, page, size)


@router.post("/backtests", summary="创建回测（异步）")
async def create_backtest(
    payload: BacktestCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    bt_id, job_id = await BacktestService(session).create_backtest(
        principal.user_id, payload
    )
    return job_accepted(bt_id, job_id)


@router.get("/backtests/{id}", summary="回测详情与进度")
async def get_backtest(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await BacktestService(session).get_backtest(principal.user_id, id)
    return success(data.model_dump())


@router.post("/backtests/{id}/cancel", summary="取消回测")
async def cancel_backtest(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    await BacktestService(session).cancel_backtest(principal.user_id, id)
    await session.commit()
    return success(message="已取消")


@router.get("/backtests/{id}/strategy", summary="回测对应的策略版本快照")
async def get_backtest_strategy(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await BacktestService(session).get_backtest_strategy(principal.user_id, id)
    return success(data.model_dump())


@router.get("/backtests/{id}/metrics", summary="绩效指标")
async def get_backtest_metrics(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await BacktestService(session).get_metrics(principal.user_id, id)
    return success(data.model_dump())


@router.get("/backtests/{id}/equity", summary="净值序列")
async def get_backtest_equity(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await BacktestService(session).get_equity(principal.user_id, id)
    return success([d.model_dump() for d in data])


@router.get("/backtests/{id}/trades", summary="交易明细")
async def list_backtest_trades(
    id: int,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await BacktestService(session).list_trades(
        principal.user_id, id, page, size
    )
    return paginated([i.model_dump() for i in items], total, page, size)


@router.get("/backtests/{id}/positions", summary="每日持仓")
async def list_backtest_positions(
    id: int,
    date: Optional[date] = Query(None, description="指定交易日，不传则返回全部"),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items = await BacktestService(session).list_positions(principal.user_id, id, date)
    return success([i.model_dump() for i in items])
