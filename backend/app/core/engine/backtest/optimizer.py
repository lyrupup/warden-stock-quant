"""参数寻优引擎：网格/随机搜索 + 批量回测 + 样本内外评估与过拟合提示。

设计：在含完整区间的单份引擎输入上，对每组参数分别在样本内(IS)/样本外(OOS)
区间执行 ``run_backtest``，仅保留绩效指标（不落逐日序列），最后按目标指标排序并
给出过拟合诊断（IS/OOS 一致性、最优解邻域稳定性）。
"""

from __future__ import annotations

import dataclasses
import itertools
import random
from datetime import date
from typing import Any, Optional

from app.core.engine.backtest.simulator import run_backtest
from app.core.engine.backtest.types import BacktestEngineInput

# 目标指标越大越好的方向（True=越大越好）
_OBJECTIVE_DIRECTION = {
    "sharpe": True,
    "sortino": True,
    "calmar": True,
    "total_return": True,
    "annual_return": True,
    "max_drawdown": True,  # 取值为负，越接近 0 越好 → 越大越好
}


def expand_param_space(param_space: dict[str, list]) -> list[dict[str, Any]]:
    """笛卡尔积展开网格参数空间。"""
    keys = [k for k, v in param_space.items() if isinstance(v, list) and v]
    if not keys:
        return [{}]
    value_lists = [param_space[k] for k in keys]
    combos = []
    for values in itertools.product(*value_lists):
        combos.append(dict(zip(keys, values)))
    return combos


def sample_param_space(
    param_space: dict[str, list], n_iter: int, seed: int = 42
) -> list[dict[str, Any]]:
    """随机搜索：从网格中无放回抽样 n_iter 组（不足则取全部）。"""
    all_combos = expand_param_space(param_space)
    if n_iter >= len(all_combos):
        return all_combos
    rng = random.Random(seed)
    return rng.sample(all_combos, n_iter)


def generate_combos(
    param_space: dict[str, list], method: str, n_iter: int = 20
) -> list[dict[str, Any]]:
    if method == "random":
        return sample_param_space(param_space, n_iter)
    return expand_param_space(param_space)


def _split_dates(calendar: list[date], oos_split: float) -> Optional[date]:
    """返回样本内最后一个交易日；oos_split<=0 时返回 None（不拆分）。"""
    days = [d for d in sorted(calendar)]
    if oos_split <= 0 or len(days) < 4:
        return None
    cut = int(len(days) * (1 - oos_split))
    cut = max(1, min(cut, len(days) - 1))
    return days[cut - 1]


def _run_segment(
    base: BacktestEngineInput,
    params: dict[str, Any],
    date_from: date,
    date_to: date,
) -> dict[str, Any]:
    seg = dataclasses.replace(
        base, params={**(base.params or {}), **params}, date_from=date_from, date_to=date_to
    )
    out = run_backtest(seg)
    return out.metrics


def _objective_value(metrics: dict[str, Any], objective: str) -> Optional[float]:
    v = metrics.get(objective)
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def run_optimization(
    base: BacktestEngineInput,
    combos: list[dict[str, Any]],
    objective: str = "sharpe",
    oos_split: float = 0.0,
    on_progress=None,
    should_cancel=None,
) -> dict[str, Any]:
    """对每组参数执行 IS/OOS 回测并汇总。

    返回 ``{"results": [...], "summary": {...}}``。
    """
    cut_date = _split_dates(base.calendar, oos_split)
    results: list[dict[str, Any]] = []
    total = max(len(combos), 1)

    for idx, params in enumerate(combos):
        if should_cancel and should_cancel():
            break
        if cut_date is not None:
            is_metrics = _run_segment(base, params, base.date_from, cut_date)
            # 样本外从切分日的下一交易日开始
            oos_dates = [d for d in sorted(base.calendar) if d > cut_date]
            oos_metrics = (
                _run_segment(base, params, oos_dates[0], base.date_to)
                if len(oos_dates) >= 2
                else None
            )
        else:
            is_metrics = _run_segment(base, params, base.date_from, base.date_to)
            oos_metrics = None

        obj = _objective_value(is_metrics, objective)
        results.append(
            {
                "params": params,
                "objective_value": obj,
                "is_metrics": is_metrics,
                "oos_metrics": oos_metrics,
            }
        )
        if on_progress:
            on_progress(round(100.0 * (idx + 1) / total, 2))

    direction = _OBJECTIVE_DIRECTION.get(objective, True)
    ranked = sorted(
        results,
        key=lambda r: (r["objective_value"] is not None, r["objective_value"] or 0.0),
        reverse=direction,
    )
    for rank, r in enumerate(ranked, start=1):
        r["rank"] = rank

    summary = _build_summary(ranked, objective, oos_split)
    return {"results": ranked, "summary": summary}


def _build_summary(
    ranked: list[dict[str, Any]], objective: str, oos_split: float
) -> dict[str, Any]:
    """过拟合诊断：最优解、IS/OOS 一致性、目标值离散度。"""
    valid = [r for r in ranked if r["objective_value"] is not None]
    if not valid:
        return {"objective": objective, "tested": len(ranked), "note": "无有效结果"}

    best = valid[0]
    values = [r["objective_value"] for r in valid]
    mean_v = sum(values) / len(values)
    var_v = sum((v - mean_v) ** 2 for v in values) / len(values)
    std_v = var_v**0.5

    summary: dict[str, Any] = {
        "objective": objective,
        "tested": len(ranked),
        "best_params": best["params"],
        "best_value": best["objective_value"],
        "value_mean": round(mean_v, 6),
        "value_std": round(std_v, 6),
    }

    # 参数平台稳定性：目标值离散度相对均值越小越稳健（最优解越不孤立）
    if abs(mean_v) > 1e-9:
        dispersion = std_v / abs(mean_v)
        summary["stability"] = round(1.0 / (1.0 + dispersion), 4)

    # IS/OOS 一致性：最优解样本外是否同向
    if oos_split > 0 and best.get("oos_metrics"):
        is_v = best["objective_value"]
        oos_v = _objective_value(best["oos_metrics"], objective)
        summary["best_oos_value"] = oos_v
        if is_v is not None and oos_v is not None:
            consistent = (is_v >= 0) == (oos_v >= 0) and oos_v >= is_v * 0.3
            summary["oos_consistent"] = bool(consistent)
            summary["overfit_warning"] = not consistent

    return summary
