"""从净值/成交/持仓序列构建 M5 绩效分析数据。"""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any, Optional

import numpy as np


def _navs(equity: list[dict[str, Any]]) -> np.ndarray:
    return np.array([float(p["nav"]) for p in equity], dtype=float)


def _bench_navs(equity: list[dict[str, Any]]) -> Optional[np.ndarray]:
    vals = [p.get("benchmark_nav") for p in equity]
    if not vals or all(v is None for v in vals):
        return None
    return np.array([float(v) if v is not None else np.nan for v in vals], dtype=float)


def _daily_returns(navs: np.ndarray) -> np.ndarray:
    if len(navs) < 2:
        return np.array([], dtype=float)
    rets = np.diff(navs) / navs[:-1]
    return rets[np.isfinite(rets)]


def compute_monthly_returns(equity: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """按自然月汇总收益率。"""
    if len(equity) < 2:
        return []
    buckets: dict[tuple[int, int], list[float]] = defaultdict(list)
    for i, p in enumerate(equity):
        d: date = p["trade_date"]
        buckets[(d.year, d.month)].append(float(p["nav"]))

    out: list[dict[str, Any]] = []
    for (year, month), navs in sorted(buckets.items()):
        if len(navs) < 2:
            ret = 0.0
        else:
            ret = navs[-1] / navs[0] - 1.0
        out.append({"year": year, "month": month, "return": round(ret, 8)})
    return out


def compute_benchmark_metrics(equity: list[dict[str, Any]]) -> dict[str, Optional[float]]:
    """相对基准的 Alpha/Beta/信息比率（日收益回归）。"""
    navs = _navs(equity)
    bench = _bench_navs(equity)
    if bench is None or len(navs) < 5:
        return {"alpha": None, "beta": None, "info_ratio": None}

    strat_rets = np.diff(navs) / navs[:-1]
    bench_rets = np.diff(bench) / bench[:-1]
    mask = np.isfinite(strat_rets) & np.isfinite(bench_rets)
    strat_rets = strat_rets[mask]
    bench_rets = bench_rets[mask]
    if len(strat_rets) < 5 or np.std(bench_rets) == 0:
        return {"alpha": None, "beta": None, "info_ratio": None}

    # OLS: strat = alpha_daily + beta * bench
    x = np.vstack([np.ones(len(bench_rets)), bench_rets]).T
    coef, _, _, _ = np.linalg.lstsq(x, strat_rets, rcond=None)
    alpha_daily, beta = float(coef[0]), float(coef[1])
    alpha_annual = alpha_daily * 252.0

    excess = strat_rets - bench_rets
    te = float(np.std(excess, ddof=1))
    ir = float(np.mean(excess) / te * np.sqrt(252)) if te > 0 else None

    return {
        "alpha": round(alpha_annual, 8),
        "beta": round(beta, 8),
        "info_ratio": round(ir, 8) if ir is not None else None,
    }


def compute_rolling_sharpe(
    equity: list[dict[str, Any]], window: int = 60
) -> list[dict[str, Any]]:
    """滚动夏普（年化，无风险利率默认 0）。"""
    navs = _navs(equity)
    if len(navs) < 2:
        return []
    daily = np.diff(navs) / navs[:-1]
    out: list[dict[str, Any]] = []
    # 首日无收益
    out.append({"trade_date": equity[0]["trade_date"], "sharpe": None})
    for i in range(1, len(equity)):
        start = max(0, i - window)
        chunk = daily[start:i]
        sharpe: Optional[float] = None
        if len(chunk) >= 5 and np.std(chunk, ddof=1) > 0:
            sharpe = float(np.mean(chunk) / np.std(chunk, ddof=1) * np.sqrt(252))
        out.append(
            {
                "trade_date": equity[i]["trade_date"],
                "sharpe": round(sharpe, 6) if sharpe is not None else None,
            }
        )
    return out


def compute_return_distribution(
    equity: list[dict[str, Any]], bins: int = 20
) -> list[dict[str, Any]]:
    """日收益分布直方图桶。"""
    navs = _navs(equity)
    rets = _daily_returns(navs)
    if len(rets) == 0:
        return []
    counts, edges = np.histogram(rets, bins=bins)
    return [
        {
            "bin_start": round(float(edges[i]), 6),
            "bin_end": round(float(edges[i + 1]), 6),
            "count": int(counts[i]),
        }
        for i in range(len(counts))
    ]


def compute_stock_attribution(trades: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """个股盈亏贡献（卖出成交 pnl 汇总）。"""
    pnl_by_code: dict[str, float] = defaultdict(float)
    count_by_code: dict[str, int] = defaultdict(int)
    for t in trades:
        if t.get("side") != "sell":
            continue
        pnl = t.get("pnl")
        if pnl is None:
            continue
        code = str(t["code"])
        pnl_by_code[code] += float(pnl)
        count_by_code[code] += 1
    ranked = sorted(pnl_by_code.items(), key=lambda x: x[1], reverse=True)
    return [
        {
            "code": code,
            "total_pnl": round(total, 4),
            "trade_count": count_by_code[code],
        }
        for code, total in ranked
    ]


def compute_concentration(positions: list[dict[str, Any]]) -> dict[str, Any]:
    """持仓集中度：日均最大权重、平均持股数。"""
    if not positions:
        return {"avg_max_weight": None, "avg_holdings": None}

    by_date: dict[date, list[float]] = defaultdict(list)
    for p in positions:
        w = p.get("weight")
        if w is None:
            continue
        by_date[p["trade_date"]].append(float(w))

    max_weights = [max(ws) for ws in by_date.values() if ws]
    holdings = [len(ws) for ws in by_date.values() if ws]
    return {
        "avg_max_weight": round(float(np.mean(max_weights)), 6) if max_weights else None,
        "avg_holdings": round(float(np.mean(holdings)), 2) if holdings else None,
    }


def build_report_analysis(
    equity: list[dict[str, Any]],
    trades: list[dict[str, Any]],
    positions: list[dict[str, Any]],
    *,
    rolling_window: int = 60,
) -> dict[str, Any]:
    """构建完整 M5 分析 JSON（供 API 与 HTML 报告消费）。"""
    drawdown_series = [
        {
            "trade_date": p["trade_date"],
            "drawdown": round(float(p["drawdown"]), 8) if p.get("drawdown") is not None else None,
        }
        for p in equity
    ]
    return {
        "benchmark_metrics": compute_benchmark_metrics(equity),
        "monthly_returns": compute_monthly_returns(equity),
        "drawdown_series": drawdown_series,
        "rolling_sharpe": compute_rolling_sharpe(equity, window=rolling_window),
        "return_distribution": compute_return_distribution(equity),
        "stock_attribution": compute_stock_attribution(trades),
        "concentration": compute_concentration(positions),
    }
