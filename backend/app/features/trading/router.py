"""M8 仿真交易 API。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.response import paginated, success
from app.core.security.deps import Principal, require_user_session
from app.features.trading.schema import OrderCreate
from app.features.trading.service import TradingService

router = APIRouter(tags=["Trading"])


@router.get("/portfolios/{id}/orders", summary="订单列表")
async def list_orders(
    id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await TradingService(session).list_orders(principal.user_id, id, page, size)
    return paginated(items, total, page, size)


@router.post("/portfolios/{id}/orders", summary="手动下单（过风控）")
async def create_order(
    id: int,
    payload: OrderCreate,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await TradingService(session).submit_order(principal.user_id, id, payload)
    return success(data, message="下单成功")


@router.post("/orders/{id}/cancel", summary="撤单")
async def cancel_order(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    data = await TradingService(session).cancel_order(principal.user_id, id)
    return success(data, message="已撤单")


@router.get("/portfolios/{id}/trades", summary="成交列表")
async def list_trades(
    id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items, total = await TradingService(session).list_trades(principal.user_id, id, page, size)
    return paginated(items, total, page, size)


@router.get("/portfolios/{id}/signals", summary="调仓信号建议")
async def list_signals(
    id: int,
    session: AsyncSession = Depends(get_session),
    principal: Principal = Depends(require_user_session),
) -> dict:
    items = await TradingService(session).list_signals(principal.user_id, id)
    return success(items)
