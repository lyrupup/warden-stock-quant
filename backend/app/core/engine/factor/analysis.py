"""因子 IC/分层分析。"""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

from app.core.engine.backtest.types import BarData
from app.core.engine.factor.compute import compute_factor_matrix


def run_factor_analysis(
    *,
    bars_by_code: dict[str, BarData],
    calendar: list[date],
    factor_name: str,
    factor_params: dict[str, Any] | None,
    direction: int,
    forward_period: int = 5,
    n_quantiles: int = 5,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, Any]:
    """计算 Rank IC、IR、分层收益等。"""
    matrix = compute_factor_matrix(
        bars_by_code, calendar, factor_name, factor_params, direction
    )
    eval_dates = [
        d
        for d in calendar
        if (date_from is None or d >= date_from) and (date_to is None or d <= date_to)
    ]
    if len(eval_dates) < forward_period + 5:
        raise ValueError("分析区间交易日不足")

    ic_rows: list[dict[str, Any]] = []
    quantile_acc: dict[int, list[float]] = {q: [] for q in range(1, n_quantiles + 1)}

    for i, dt in enumerate(calendar):
        if dt not in eval_dates:
            continue
        if i + forward_period >= len(calendar):
            break
        fwd_date = calendar[i + forward_period]
        factor_vals: list[float] = []
        fwd_rets: list[float] = []
        for code, arr in matrix.items():
            fv = arr[i]
            if np.isnan(fv):
                continue
            bars = bars_by_code.get(code)
            if not bars:
                continue
            c_map = {d: bars.close[j] for j, d in enumerate(bars.dates)}
            p0 = c_map.get(dt)
            p1 = c_map.get(fwd_date)
            if p0 is None or p1 is None or p0 <= 0:
                continue
            factor_vals.append(float(fv))
            fwd_rets.append(float(p1 / p0 - 1.0))

        if len(factor_vals) < 2:
            continue
        rank_ic, _ = stats.spearmanr(factor_vals, fwd_rets)
        if np.isnan(rank_ic):
            continue
        ic_rows.append({"trade_date": dt.isoformat(), "ic": float(rank_ic)})

        df = pd.DataFrame({"factor": factor_vals, "ret": fwd_rets})
        effective_q = min(n_quantiles, len(df))
        if effective_q < 2:
            continue
        try:
            df["q"] = pd.qcut(df["factor"], effective_q, labels=False, duplicates="drop") + 1
        except ValueError:
            continue
        for q in range(1, effective_q + 1):
            sub = df[df["q"] == q]["ret"]
            if len(sub):
                quantile_acc[q].append(float(sub.mean()))

    if not ic_rows:
        raise ValueError("有效 IC 样本不足，请扩大区间或检查因子数据")

    ic_vals = [r["ic"] for r in ic_rows]
    ic_mean = float(np.mean(ic_vals))
    ic_std = float(np.std(ic_vals, ddof=1)) if len(ic_vals) > 1 else 0.0
    ic_ir = ic_mean / ic_std if ic_std > 1e-12 else 0.0
    ic_win_rate = float(np.mean([1 if v > 0 else 0 for v in ic_vals]))

    quantile_returns = {
        f"Q{q}": float(np.mean(rets)) if rets else 0.0
        for q, rets in quantile_acc.items()
    }
    long_short = quantile_returns.get(f"Q{n_quantiles}", 0) - quantile_returns.get("Q1", 0)

    return {
        "ic_mean": ic_mean,
        "ic_ir": ic_ir,
        "ic_win_rate": ic_win_rate,
        "ic_series": ic_rows,
        "quantile_returns": quantile_returns,
        "turnover": {"long_short_spread": long_short, "samples": len(ic_rows)},
    }
