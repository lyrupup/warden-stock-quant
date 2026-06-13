"""回测数据加载：从 DataFeed 构建引擎输入。"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data.feed.pg_feed import BarRow, PgDataFeed
from app.core.engine.backtest.types import BacktestEngineInput, BarData, CostModel
from app.features.datasets.models import MarketSecurity


def _to_float(v: Optional[Decimal]) -> Optional[float]:
    return float(v) if v is not None else None


def bar_row_to_data(code: str, rows: list[BarRow]) -> BarData:
    return BarData(
        code=code,
        dates=[r.trade_date for r in rows],
        open=[_to_float(r.open) or 0.0 for r in rows],
        high=[_to_float(r.high) or 0.0 for r in rows],
        low=[_to_float(r.low) or 0.0 for r in rows],
        close=[_to_float(r.close) or 0.0 for r in rows],
        suspended=[bool(r.suspended) for r in rows],
        limit_up=[_to_float(r.limit_up) for r in rows],
        limit_down=[_to_float(r.limit_down) for r in rows],
    )


async def resolve_universe_codes(
    session: AsyncSession,
    universe: Optional[dict[str, Any]],
    max_codes: int = 50,
) -> list[str]:
    """解析股票池为代码列表（首期：list / all 限流）。"""
    if not universe or universe.get("type") == "all":
        rows = (
            await session.execute(
                select(MarketSecurity.code)
                .where(MarketSecurity.status == "listed")
                .order_by(MarketSecurity.code)
                .limit(max_codes)
            )
        ).scalars().all()
        return list(rows)
    if universe.get("type") == "list":
        codes = universe.get("codes") or []
        return [str(c).strip() for c in codes if c][:max_codes]
    if universe.get("type") == "index":
        # 指数成分待上游 API，暂降级为单代码或空
        code = universe.get("code")
        return [str(code)] if code else []
    return []


async def build_engine_input(
    session: AsyncSession,
    *,
    date_from: date,
    date_to: date,
    init_capital: float,
    adjust: str,
    cost_config: Optional[dict[str, Any]],
    strategy_config: dict[str, Any],
    universe: Optional[dict[str, Any]],
    params: Optional[dict[str, Any]],
    benchmark: str = "000300",
    max_codes: int = 50,
    user_id: Optional[int] = None,
) -> BacktestEngineInput:
    feed = PgDataFeed(session)
    warmup = date_from - timedelta(days=120)
    calendar = await feed.trading_calendar(warmup, date_to)
    codes = await resolve_universe_codes(session, universe, max_codes=max_codes)
    if not codes:
        raise ValueError("股票池为空，请检查 universe 配置或本地数据集")

    bars_by_code: dict[str, BarData] = {}
    for code in codes:
        rows = await feed.get_bars(code, warmup, date_to, adjust=adjust)
        if rows:
            bars_by_code[code] = bar_row_to_data(code, rows)

    if not bars_by_code:
        raise ValueError("选定股票池在回测区间内无行情数据")

    bench_rows = await feed.get_bars(benchmark, warmup, date_to, adjust=adjust)
    benchmark_bars = bar_row_to_data(benchmark, bench_rows) if bench_rows else None

    factor_matrix = None
    factor_top = 0.1
    signals = (strategy_config or {}).get("signals") or []
    if signals and signals[0].get("type") == "factor_rank":
        from app.core.engine.factor.compute import compute_factor_matrix

        sig = signals[0]
        factor_name = str(sig.get("factor", "momentum_20"))
        factor_top = float(sig.get("top", 0.1))
        direction = 1
        factor_params = params
        if user_id is not None:
            from app.features.factors.repository import FactorRepository

            repo = FactorRepository(session)
            custom = await repo.get_by_name(user_id, factor_name)
            if custom is not None:
                factor_name = custom.expr or custom.name
                factor_params = custom.params
                direction = custom.direction
        factor_matrix = compute_factor_matrix(
            bars_by_code, calendar, factor_name, factor_params, direction
        )

    return BacktestEngineInput(
        date_from=date_from,
        date_to=date_to,
        init_capital=init_capital,
        adjust=adjust,
        cost=CostModel.from_dict(cost_config),
        strategy_config=strategy_config,
        universe_codes=list(bars_by_code.keys()),
        params=params or {},
        benchmark_bars=benchmark_bars,
        bars_by_code=bars_by_code,
        calendar=calendar,
        factor_matrix=factor_matrix,
        factor_top=factor_top,
    )
