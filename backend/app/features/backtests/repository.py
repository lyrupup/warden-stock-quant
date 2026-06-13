"""M4 回测数据访问。"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.backtests.models import (
    Backtest,
    BacktestDailyPosition,
    BacktestEquity,
    BacktestMetric,
    BacktestOptimization,
    BacktestOptimizationResult,
    BacktestTrade,
)


class BacktestRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, bt: Backtest) -> Backtest:
        self._session.add(bt)
        await self._session.flush()
        return bt

    async def get_owned(self, backtest_id: int, user_id: int) -> Optional[Backtest]:
        return (
            await self._session.execute(
                select(Backtest).where(Backtest.id == backtest_id, Backtest.user_id == user_id)
            )
        ).scalar_one_or_none()

    async def list_by_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[Sequence[Backtest], int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count()).select_from(Backtest).where(Backtest.user_id == user_id)
                )
            ).scalar_one()
        )
        offset = max(page - 1, 0) * size
        rows = (
            await self._session.execute(
                select(Backtest)
                .where(Backtest.user_id == user_id)
                .order_by(Backtest.created_at.desc())
                .offset(offset)
                .limit(size)
            )
        ).scalars().all()
        return rows, total

    async def count_active(self, user_id: int) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(Backtest)
                    .where(
                        Backtest.user_id == user_id,
                        Backtest.status.in_(("queued", "running")),
                    )
                )
            ).scalar_one()
        )

    async def update_status(
        self,
        backtest_id: int,
        *,
        status: Optional[str] = None,
        progress: Optional[Decimal] = None,
        error: Optional[str] = None,
        job_id: Optional[str] = None,
        finished_at: Any = None,
    ) -> None:
        bt = (
            await self._session.execute(select(Backtest).where(Backtest.id == backtest_id))
        ).scalar_one()
        if status is not None:
            bt.status = status
        if progress is not None:
            bt.progress = progress
        if error is not None:
            bt.error = error
        if job_id is not None:
            bt.job_id = job_id
        if finished_at is not None:
            bt.finished_at = finished_at
        await self._session.flush()

    async def save_results(
        self,
        backtest_id: int,
        metrics: dict[str, Any],
        equity: list[dict[str, Any]],
        trades: list[dict[str, Any]],
        positions: list[dict[str, Any]],
    ) -> None:
        metric = BacktestMetric(backtest_id=backtest_id, **metrics)
        self._session.add(metric)
        for row in equity:
            self._session.add(BacktestEquity(backtest_id=backtest_id, **row))
        for row in trades:
            self._session.add(BacktestTrade(backtest_id=backtest_id, **row))
        for row in positions:
            self._session.add(BacktestDailyPosition(backtest_id=backtest_id, **row))
        await self._session.flush()

    async def get_metrics(self, backtest_id: int) -> Optional[BacktestMetric]:
        return (
            await self._session.execute(
                select(BacktestMetric).where(BacktestMetric.backtest_id == backtest_id)
            )
        ).scalar_one_or_none()

    async def list_equity(self, backtest_id: int) -> Sequence[BacktestEquity]:
        return (
            await self._session.execute(
                select(BacktestEquity)
                .where(BacktestEquity.backtest_id == backtest_id)
                .order_by(BacktestEquity.trade_date)
            )
        ).scalars().all()

    async def list_trades(
        self, backtest_id: int, page: int, size: int
    ) -> tuple[Sequence[BacktestTrade], int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(BacktestTrade)
                    .where(BacktestTrade.backtest_id == backtest_id)
                )
            ).scalar_one()
        )
        offset = max(page - 1, 0) * size
        rows = (
            await self._session.execute(
                select(BacktestTrade)
                .where(BacktestTrade.backtest_id == backtest_id)
                .order_by(BacktestTrade.trade_date, BacktestTrade.id)
                .offset(offset)
                .limit(size)
            )
        ).scalars().all()
        return rows, total

    async def list_positions(
        self, backtest_id: int, trade_date: Optional[date] = None
    ) -> Sequence[BacktestDailyPosition]:
        stmt = select(BacktestDailyPosition).where(
            BacktestDailyPosition.backtest_id == backtest_id
        )
        if trade_date:
            stmt = stmt.where(BacktestDailyPosition.trade_date == trade_date)
        stmt = stmt.order_by(
            BacktestDailyPosition.trade_date, BacktestDailyPosition.code
        )
        return (await self._session.execute(stmt)).scalars().all()


class OptimizationRepository:
    """参数寻优数据访问（强制租户作用域）。"""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, opt: BacktestOptimization) -> BacktestOptimization:
        self._session.add(opt)
        await self._session.flush()
        return opt

    async def get_owned(
        self, optimization_id: int, user_id: int
    ) -> Optional[BacktestOptimization]:
        return (
            await self._session.execute(
                select(BacktestOptimization).where(
                    BacktestOptimization.id == optimization_id,
                    BacktestOptimization.user_id == user_id,
                )
            )
        ).scalar_one_or_none()

    async def list_by_user(
        self, user_id: int, page: int, size: int
    ) -> tuple[Sequence[BacktestOptimization], int]:
        total = int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(BacktestOptimization)
                    .where(BacktestOptimization.user_id == user_id)
                )
            ).scalar_one()
        )
        offset = max(page - 1, 0) * size
        rows = (
            await self._session.execute(
                select(BacktestOptimization)
                .where(BacktestOptimization.user_id == user_id)
                .order_by(BacktestOptimization.created_at.desc())
                .offset(offset)
                .limit(size)
            )
        ).scalars().all()
        return rows, total

    async def count_active(self, user_id: int) -> int:
        return int(
            (
                await self._session.execute(
                    select(func.count())
                    .select_from(BacktestOptimization)
                    .where(
                        BacktestOptimization.user_id == user_id,
                        BacktestOptimization.status.in_(("queued", "running")),
                    )
                )
            ).scalar_one()
        )

    async def update_status(
        self,
        optimization_id: int,
        *,
        status: Optional[str] = None,
        progress: Optional[Decimal] = None,
        error: Optional[str] = None,
        job_id: Optional[str] = None,
        summary: Optional[dict[str, Any]] = None,
        finished_at: Any = None,
    ) -> None:
        opt = (
            await self._session.execute(
                select(BacktestOptimization).where(
                    BacktestOptimization.id == optimization_id
                )
            )
        ).scalar_one()
        if status is not None:
            opt.status = status
        if progress is not None:
            opt.progress = progress
        if error is not None:
            opt.error = error
        if job_id is not None:
            opt.job_id = job_id
        if summary is not None:
            opt.summary = summary
        if finished_at is not None:
            opt.finished_at = finished_at
        await self._session.flush()

    async def save_results(
        self, optimization_id: int, results: list[dict[str, Any]]
    ) -> None:
        for r in results:
            self._session.add(
                BacktestOptimizationResult(optimization_id=optimization_id, **r)
            )
        await self._session.flush()

    async def list_results(
        self, optimization_id: int
    ) -> Sequence[BacktestOptimizationResult]:
        return (
            await self._session.execute(
                select(BacktestOptimizationResult)
                .where(BacktestOptimizationResult.optimization_id == optimization_id)
                .order_by(BacktestOptimizationResult.rank)
            )
        ).scalars().all()
