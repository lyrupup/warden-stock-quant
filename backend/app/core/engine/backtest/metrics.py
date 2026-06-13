"""绩效指标计算。"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import numpy as np

from app.core.engine.backtest.types import EquityPoint, TradeRecord


def compute_metrics(
    equity: list[EquityPoint],
    trades: list[TradeRecord],
    init_capital: float,
) -> dict[str, Any]:
    """从净值序列与成交记录计算核心绩效指标。"""
    if not equity or init_capital <= 0:
        return _empty_metrics()

    navs = np.array([p.nav for p in equity], dtype=float)
    dates = [p.trade_date for p in equity]
    total_return = float(navs[-1] / init_capital - 1.0)

    daily_rets = np.diff(navs) / navs[:-1]
    daily_rets = daily_rets[np.isfinite(daily_rets)]
    n_days = max(len(daily_rets), 1)
    annual_factor = 252.0 / n_days if n_days else 1.0

    annual_return = float((1.0 + total_return) ** annual_factor - 1.0) if n_days else 0.0
    volatility = float(np.std(daily_rets, ddof=1) * np.sqrt(252)) if len(daily_rets) > 1 else 0.0
    mean_ret = float(np.mean(daily_rets)) if len(daily_rets) else 0.0
    sharpe = float(mean_ret / np.std(daily_rets, ddof=1) * np.sqrt(252)) if len(daily_rets) > 1 and np.std(daily_rets) > 0 else 0.0

    downside = daily_rets[daily_rets < 0]
    sortino = (
        float(mean_ret / np.std(downside, ddof=1) * np.sqrt(252))
        if len(downside) > 1 and np.std(downside) > 0
        else 0.0
    )

    peak = np.maximum.accumulate(navs)
    dd = (navs - peak) / peak
    max_drawdown = float(np.min(dd)) if len(dd) else 0.0
    mdd_idx = int(np.argmin(dd)) if len(dd) else 0
    mdd_from, mdd_to = _mdd_range(dates, navs, mdd_idx)

    calmar = float(annual_return / abs(max_drawdown)) if max_drawdown < 0 else 0.0

    sell_trades = [t for t in trades if t.side == "sell" and t.pnl is not None]
    wins = [t for t in sell_trades if t.pnl and t.pnl > 0]
    win_rate = float(len(wins) / len(sell_trades)) if sell_trades else 0.0
    gross_profit = sum(t.pnl for t in sell_trades if t.pnl and t.pnl > 0)
    gross_loss = abs(sum(t.pnl for t in sell_trades if t.pnl and t.pnl < 0))
    profit_factor = float(gross_profit / gross_loss) if gross_loss > 0 else 0.0

    turnover = _estimate_turnover(trades, init_capital, n_days)

    return {
        "total_return": round(total_return, 8),
        "annual_return": round(annual_return, 8),
        "volatility": round(volatility, 8),
        "sharpe": round(sharpe, 8),
        "sortino": round(sortino, 8),
        "calmar": round(calmar, 8),
        "max_drawdown": round(max_drawdown, 8),
        "mdd_from": mdd_from,
        "mdd_to": mdd_to,
        "win_rate": round(win_rate, 8),
        "profit_factor": round(profit_factor, 8),
        "turnover": round(turnover, 8),
        "alpha": None,
        "beta": None,
        "info_ratio": None,
    }


def _empty_metrics() -> dict[str, Any]:
    return {
        "total_return": 0.0,
        "annual_return": 0.0,
        "volatility": 0.0,
        "sharpe": 0.0,
        "sortino": 0.0,
        "calmar": 0.0,
        "max_drawdown": 0.0,
        "mdd_from": None,
        "mdd_to": None,
        "win_rate": 0.0,
        "profit_factor": 0.0,
        "turnover": 0.0,
        "alpha": None,
        "beta": None,
        "info_ratio": None,
    }


def _mdd_range(dates: list[date], navs: np.ndarray, mdd_idx: int) -> tuple[Optional[date], Optional[date]]:
    if not dates or mdd_idx <= 0:
        return None, None
    peak_idx = int(np.argmax(navs[: mdd_idx + 1]))
    return dates[peak_idx], dates[mdd_idx]


def _estimate_turnover(trades: list[TradeRecord], init_capital: float, n_days: int) -> float:
    if init_capital <= 0 or not trades:
        return 0.0
    total_amount = sum(abs(t.amount) for t in trades)
    years = max(n_days / 252.0, 1 / 252.0)
    return float(total_amount / init_capital / years)
