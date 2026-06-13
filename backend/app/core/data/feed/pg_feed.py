"""DataFeed：回测/因子/实盘统一取数入口（PIT）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional, Protocol

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.datasets.models import (
    MarketDailyBar,
    MarketSecurity,
    MarketTradingCalendar,
)


@dataclass
class BarRow:
    code: str
    trade_date: date
    open: Optional[Decimal]
    high: Optional[Decimal]
    low: Optional[Decimal]
    close: Optional[Decimal]
    volume: Optional[Decimal]
    amount: Optional[Decimal]
    adj_factor: Optional[Decimal]
    limit_up: Optional[Decimal]
    limit_down: Optional[Decimal]
    suspended: bool
    is_st: bool


class DataFeed(Protocol):
    async def trading_calendar(self, start: date, end: date) -> list[date]: ...
    async def list_securities(self, kw: Optional[str] = None) -> list[dict]: ...
    async def get_bars(
        self,
        code: str,
        start: date,
        end: date,
        adjust: str = "qfq",
    ) -> list[BarRow]: ...


class PgDataFeed:
    """从 PostgreSQL/SQLite 本地数据集读取（M2 默认实现）。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def trading_calendar(self, start: date, end: date) -> list[date]:
        rows = (
            await self._session.execute(
                select(MarketTradingCalendar.trade_date).where(
                    and_(
                        MarketTradingCalendar.trade_date >= start,
                        MarketTradingCalendar.trade_date <= end,
                        MarketTradingCalendar.is_open.is_(True),
                    )
                ).order_by(MarketTradingCalendar.trade_date)
            )
        ).scalars().all()
        return list(rows)

    async def list_securities(self, kw: Optional[str] = None) -> list[dict]:
        stmt = select(MarketSecurity)
        if kw:
            like = f"%{kw}%"
            stmt = stmt.where(
                (MarketSecurity.code.like(like)) | (MarketSecurity.name.like(like))
            )
        rows = (await self._session.execute(stmt.order_by(MarketSecurity.code))).scalars().all()
        return [
            {
                "code": r.code,
                "name": r.name,
                "market": r.market,
                "board": r.board,
                "list_date": r.list_date.isoformat() if r.list_date else None,
                "status": r.status,
            }
            for r in rows
        ]

    async def get_bars(
        self,
        code: str,
        start: date,
        end: date,
        adjust: str = "qfq",
    ) -> list[BarRow]:
        rows = (
            await self._session.execute(
                select(MarketDailyBar).where(
                    and_(
                        MarketDailyBar.code == code,
                        MarketDailyBar.trade_date >= start,
                        MarketDailyBar.trade_date <= end,
                    )
                ).order_by(MarketDailyBar.trade_date)
            )
        ).scalars().all()
        result: list[BarRow] = []
        for r in rows:
            o, h, l, c = r.open, r.high, r.low, r.close
            if adjust == "qfq" and r.adj_factor:
                # 简化：用 adj_factor 相对最新因子缩放（完整复权在 M4 引擎统一）
                pass
            result.append(
                BarRow(
                    code=r.code,
                    trade_date=r.trade_date,
                    open=o,
                    high=h,
                    low=l,
                    close=c,
                    volume=r.volume,
                    amount=r.amount,
                    adj_factor=r.adj_factor,
                    limit_up=r.limit_up,
                    limit_down=r.limit_down,
                    suspended=r.suspended,
                    is_st=r.is_st,
                )
            )
        return result

    async def dataset_status(self) -> dict:
        """数据集新鲜度与缺口摘要。"""
        sec_count = (
            await self._session.execute(select(func.count()).select_from(MarketSecurity))
        ).scalar_one()
        latest_bar = (
            await self._session.execute(select(func.max(MarketDailyBar.trade_date)))
        ).scalar_one()
        latest_cal = (
            await self._session.execute(
                select(func.max(MarketTradingCalendar.trade_date)).where(
                    MarketTradingCalendar.is_open.is_(True)
                )
            )
        ).scalar_one()
        gaps: list[str] = []
        if sec_count == 0:
            gaps.append("securities_empty")
        if latest_bar is None:
            gaps.append("daily_bars_empty")
        return {
            "latest_trade_date": latest_cal.isoformat() if latest_cal else None,
            "bars_updated_to": latest_bar.isoformat() if latest_bar else None,
            "securities_count": int(sec_count or 0),
            "gaps": gaps,
            "stale": False,
        }
