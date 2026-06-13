"""参数寻优引擎单测（纯逻辑，不依赖 DB）。"""

from __future__ import annotations

from datetime import date, timedelta

from app.core.engine.backtest.optimizer import (
    expand_param_space,
    generate_combos,
    run_optimization,
)
from app.core.engine.backtest.types import BacktestEngineInput, BarData, CostModel


def _bars(code: str, start: date, n: int) -> BarData:
    dates = [start + timedelta(days=i) for i in range(n)]
    closes = [10 + i * 0.4 for i in range(n)]
    return BarData(
        code=code,
        dates=dates,
        open=closes,
        high=[c + 0.2 for c in closes],
        low=[c - 0.2 for c in closes],
        close=closes,
        suspended=[False] * n,
        limit_up=[None] * n,
        limit_down=[None] * n,
    )


def test_expand_param_space_cartesian():
    space = {"fast": [3, 5], "slow": [15, 20, 30]}
    combos = expand_param_space(space)
    assert len(combos) == 6
    assert {"fast": 3, "slow": 15} in combos


def test_generate_combos_random_caps_iterations():
    space = {"fast": [3, 5, 8], "slow": [15, 20, 30, 40]}  # 12 combos
    combos = generate_combos(space, method="random", n_iter=5)
    assert len(combos) == 5
    # 随机抽样可复现（固定 seed）
    combos2 = generate_combos(space, method="random", n_iter=5)
    assert combos == combos2


def test_run_optimization_ranks_and_summarizes():
    start = date(2024, 1, 2)
    n = 80
    calendar = [start + timedelta(days=i) for i in range(n)]
    bars = {"600000": _bars("600000", start, n)}
    base = BacktestEngineInput(
        date_from=start,
        date_to=start + timedelta(days=n - 1),
        init_capital=1_000_000.0,
        adjust="qfq",
        cost=CostModel(),
        strategy_config={
            "signals": [{"type": "ma_cross", "fast": 5, "slow": 20}],
            "rebalance": {"freq": "day"},
            "position": {"scheme": "equal_weight", "max_n": 1},
        },
        universe_codes=["600000"],
        bars_by_code=bars,
        calendar=calendar,
    )
    combos = generate_combos({"fast": [3, 5], "slow": [15, 20]}, method="grid")
    outcome = run_optimization(base, combos, objective="sharpe", oos_split=0.3)

    results = outcome["results"]
    assert len(results) == 4
    # rank 连续且从 1 开始
    assert [r["rank"] for r in results] == [1, 2, 3, 4]
    # 每组都有样本内/样本外指标
    assert all(r["is_metrics"] is not None for r in results)
    assert all(r["oos_metrics"] is not None for r in results)

    summary = outcome["summary"]
    assert summary["objective"] == "sharpe"
    assert summary["tested"] == 4
    assert "best_params" in summary
    assert "best_oos_value" in summary
