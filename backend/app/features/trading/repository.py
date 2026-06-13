"""M8 交易数据访问。"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.trading.models import Order, Trade


class TradingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_order(self, order: Order) -> Order:
        self._session.add(order)
        await self._session.flush()
        return order

    async def get_order(self, order_id: int, user_id: int) -> Optional[Order]:
        return (
            await self._session.execute(
                select(Order).where(Order.id == order_id, Order.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def list_orders(self, portfolio_id: int, page: int, size: int) -> tuple[list[Order], int]:
        base = (
            select(Order)
            .where(Order.portfolio_id == portfolio_id)
            .order_by(Order.id.desc())
        )
        rows = (await self._session.execute(base)).scalars().all()
        total = len(rows)
        start = (page - 1) * size
        return list(rows[start : start + size]), total

    async def list_trades(self, portfolio_id: int, page: int, size: int) -> tuple[list[Trade], int]:
        base = (
            select(Trade)
            .where(Trade.portfolio_id == portfolio_id)
            .order_by(Trade.id.desc())
        )
        rows = (await self._session.execute(base)).scalars().all()
        total = len(rows)
        start = (page - 1) * size
        return list(rows[start : start + size]), total

    async def add_trade(self, trade: Trade) -> Trade:
        self._session.add(trade)
        await self._session.flush()
        return trade

    async def sum_daily_amount(self, portfolio_id: int, trade_date: date) -> float:
        stmt = select(func.coalesce(func.sum(Trade.amount), 0)).where(
            Trade.portfolio_id == portfolio_id,
            func.date(Trade.trade_time) == trade_date.isoformat(),
        )
        val = (await self._session.execute(stmt)).scalar_one()
        return float(val or 0)
