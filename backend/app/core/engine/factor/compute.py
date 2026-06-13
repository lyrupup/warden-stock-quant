"""因子计算引擎（PIT，不依赖 FastAPI）。"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

import numpy as np
import pandas as pd

from app.core.engine.backtest.types import BarData

BUILTIN_FACTORS: dict[str, dict[str, Any]] = {
    "momentum_5": {"category": "momentum", "window": 5},
    "momentum_10": {"category": "momentum", "window": 10},
    "momentum_20": {"category": "momentum", "window": 20},
    "momentum_60": {"category": "momentum", "window": 60},
    "volatility_20": {"category": "volatility", "window": 20},
    "rsi_14": {"category": "rsi", "window": 14},
}


def list_builtin_factors() -> list[dict[str, Any]]:
    return [
        {"name": name, "type": "builtin", "category": meta["category"], "params": meta}
        for name, meta in BUILTIN_FACTORS.items()
    ]


def resolve_builtin_window(factor_name: str, params: Optional[dict] = None) -> int:
    if factor_name in BUILTIN_FACTORS:
        return int(BUILTIN_FACTORS[factor_name].get("window", 20))
    if params and "window" in params:
        return int(params["window"])
    # momentum_N / volatility_N / rsi_N
    for prefix in ("momentum_", "volatility_", "rsi_"):
        if factor_name.startswith(prefix):
            try:
                return int(factor_name.split("_", 1)[1])
            except ValueError:
                pass
    return 20


def _compute_series(closes: pd.Series, factor_name: str, window: int) -> pd.Series:
    if factor_name.startswith("momentum") or "momentum" in factor_name:
        return closes.pct_change(window)
    if factor_name.startswith("volatility") or "volatility" in factor_name:
        return closes.pct_change().rolling(window, min_periods=window).std()
    if factor_name.startswith("rsi") or "rsi" in factor_name:
        delta = closes.diff()
        gain = delta.clip(lower=0.0)
        loss = (-delta).clip(lower=0.0)
        avg_gain = gain.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
        avg_loss = loss.ewm(alpha=1.0 / window, min_periods=window, adjust=False).mean()
        rs = avg_gain / avg_loss.replace(0.0, np.nan)
        rsi = 100.0 - 100.0 / (1.0 + rs)
        return rsi.where(avg_loss != 0.0, 100.0)
    return closes.pct_change(window)


def compute_factor_matrix(
    bars_by_code: dict[str, BarData],
    calendar: list[date],
    factor_name: str,
    params: Optional[dict] = None,
    direction: int = 1,
) -> dict[str, np.ndarray]:
    """按 calendar 计算每标的因子值序列（与 calendar 等长）。"""
    window = resolve_builtin_window(factor_name, params)
    date_index = {d: i for i, d in enumerate(calendar)}
    result: dict[str, np.ndarray] = {}
    for code, bars in bars_by_code.items():
        date_to_close = {d: bars.close[j] for j, d in enumerate(bars.dates)}
        closes = pd.Series(
            [date_to_close.get(d, np.nan) for d in calendar],
            dtype=float,
        )
        series = _compute_series(closes, factor_name, window)
        if direction < 0:
            series = -series
        result[code] = series.to_numpy(dtype=float)
    return result


def values_for_date(
    matrix: dict[str, np.ndarray], calendar: list[date], trade_date: date
) -> dict[str, float]:
    """提取某日截面因子值（过滤 NaN）。"""
    idx = calendar.index(trade_date)
    out: dict[str, float] = {}
    for code, arr in matrix.items():
        v = arr[idx]
        if v is not None and not np.isnan(v):
            out[code] = float(v)
    return out
