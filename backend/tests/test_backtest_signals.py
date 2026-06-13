"""信号计算层单测：覆盖 ma_cross/ma_trend/rsi/bollinger/macd 与多信号回测。"""

from __future__ import annotations

import math
from datetime import date, timedelta

import numpy as np

from app.core.engine.backtest.signals import (
    compute_hold_states,
    compute_ma_trend_layers,
    is_supported,
)
from app.core.engine.backtest.simulator import run_backtest
from app.core.engine.backtest.types import BacktestEngineInput, BarData, CostModel


def _bars(code: str, start: date, closes: list[float]) -> BarData:
    n = len(closes)
    dates = [start + timedelta(days=i) for i in range(n)]
    return BarData(
        code=code,
        dates=dates,
        open=list(closes),
        high=[c + 0.2 for c in closes],
        low=[c - 0.2 for c in closes],
        close=list(closes),
        suspended=[False] * n,
        limit_up=[None] * n,
        limit_down=[None] * n,
    )


def test_supported_signals():
    for t in ("ma_cross", "ma_trend", "rsi", "bollinger", "macd"):
        assert is_supported(t)
    assert not is_supported("unknown_signal")


def test_ma_trend_states_detect_bull_alignment():
    start = date(2024, 1, 2)
    # 单调上涨 → 长期均线多头排列成立
    closes = [10 + i * 0.5 for i in range(40)]
    calendar = [start + timedelta(days=i) for i in range(40)]
    bars = {"600000": _bars("600000", start, closes)}
    states = compute_hold_states(
        {"type": "ma_trend", "periods": [5, 10, 20]}, {}, bars, calendar
    )
    arr = states["600000"]
    # 预热不足处为 False，尾部多头排列成立处为 True
    assert not arr[:19].any()
    assert arr[-1]


def test_rsi_state_machine_enters_on_oversold():
    start = date(2024, 1, 2)
    # 先跌后涨：制造低 RSI 进场，再高 RSI 出场
    down = [20 - i * 0.4 for i in range(20)]
    up = [down[-1] + i * 0.8 for i in range(1, 21)]
    closes = down + up
    calendar = [start + timedelta(days=i) for i in range(len(closes))]
    bars = {"600000": _bars("600000", start, closes)}
    states = compute_hold_states(
        {"type": "rsi", "period": 6, "oversold": 35, "overbought": 70}, {}, bars, calendar
    )
    arr = states["600000"]
    # 序列里应至少出现一次持仓
    assert arr.any()


def test_bollinger_mean_reversion_holds_between_bands():
    start = date(2024, 1, 2)
    # 制造一个下破后回归的形态
    closes = [50.0] * 25 + [40.0] + [42.0, 45.0, 48.0, 51.0]
    calendar = [start + timedelta(days=i) for i in range(len(closes))]
    bars = {"600000": _bars("600000", start, closes)}
    states = compute_hold_states(
        {"type": "bollinger", "period": 20, "std": 2.0}, {}, bars, calendar
    )
    arr = states["600000"]
    assert isinstance(arr, np.ndarray)
    assert arr.dtype == bool


def test_macd_states_bullish_on_uptrend():
    start = date(2024, 1, 2)
    closes = [10 + i * 0.3 for i in range(60)]
    calendar = [start + timedelta(days=i) for i in range(60)]
    bars = {"600000": _bars("600000", start, closes)}
    states = compute_hold_states(
        {"type": "macd", "fast": 12, "slow": 26, "signal": 9}, {}, bars, calendar
    )
    arr = states["600000"]
    # 持续上涨末段 DIF 应高于 DEA
    assert arr[-1]


def _run_with_signal(signal: dict, closes: list[float]) -> None:
    start = date(2024, 1, 2)
    calendar = [start + timedelta(days=i) for i in range(len(closes))]
    bars = _bars("600000", start, closes)
    inp = BacktestEngineInput(
        date_from=start,
        date_to=start + timedelta(days=len(closes) - 1),
        init_capital=1_000_000.0,
        adjust="qfq",
        cost=CostModel(),
        strategy_config={
            "signals": [signal],
            "rebalance": {"freq": "day"},
            "position": {"scheme": "equal_weight", "max_n": 1},
        },
        universe_codes=["600000"],
        bars_by_code={"600000": bars},
        calendar=calendar,
    )
    out = run_backtest(inp)
    assert len(out.equity) == len(closes)
    assert out.equity[-1].nav > 0
    assert math.isfinite(float(out.metrics["total_return"]))


def test_backtest_runs_for_each_breadth_signal():
    up = [10 + i * 0.4 for i in range(60)]
    _run_with_signal({"type": "ma_trend", "periods": [5, 10, 20]}, up)
    _run_with_signal({"type": "macd"}, up)
    _run_with_signal({"type": "rsi", "period": 6}, up)
    _run_with_signal({"type": "bollinger", "period": 20}, up)


def test_ma_trend_layers_entry_and_add():
    start = date(2024, 1, 2)
    closes = [10 + i * 0.5 for i in range(70)]
    calendar = [start + timedelta(days=i) for i in range(70)]
    bars = {"600000": _bars("600000", start, closes)}
    layers = compute_ma_trend_layers(
        {
            "type": "ma_trend",
            "launch": {
                "bias_ma": 5,
                "bias_range": [0.0, 0.5],
                "slope_ma": 5,
                "slope_window": 5,
                "above_ma": 5,
                "above_ratio": 0.8,
                "above_window": 10,
            },
            "tiers": [
                {"mas": [5, 10, 20], "role": "entry"},
                {"mas": [20, 30, 40], "role": "add"},
            ],
        },
        {},
        bars,
        calendar,
    )
    lyr = layers["600000"]
    # 持续上涨：尾部短期与中期排列均成立
    assert lyr["trend"][-1]
    assert lyr["add"][-1]
    assert lyr["entry"].any()


def test_pyramid_scale_in_increases_position():
    """金字塔：上涨趋势中应先建观察仓再分批加仓，最终持仓占比高于初始。"""
    from app.core.engine.backtest.compiler import ConfigStrategyCompiler
    from app.core.engine.backtest.simulator import run_backtest

    start = date(2024, 1, 2)
    closes = [10 + i * 0.5 for i in range(70)]
    calendar = [start + timedelta(days=i) for i in range(70)]
    bars = _bars("600000", start, closes)
    config = {
        "signals": [
            {
                "type": "ma_trend",
                "launch": {"bias_range": [0.0, 0.6], "above_ratio": 0.6, "above_window": 5},
                "tiers": [
                    {"mas": [5, 10, 20], "role": "entry"},
                    {"mas": [20, 30, 40], "role": "add"},
                ],
            }
        ],
        "rebalance": {"freq": "day"},
        "position": {
            "scheme": "pyramid",
            "max_n": 1,
            "scale_in": {
                "init_weight": 0.4,
                "observe_days": 2,
                "add_steps": 2,
                "add_weight": 0.3,
                "trigger": "medium_align",
            },
        },
        "stop": {"stop_loss": 0.2, "trailing": 0.3, "observe_stop_loss": 0.05},
    }
    compiler = ConfigStrategyCompiler(config)
    assert compiler.is_pyramid
    inp = BacktestEngineInput(
        date_from=start,
        date_to=start + timedelta(days=69),
        init_capital=1_000_000.0,
        adjust="qfq",
        cost=CostModel(),
        strategy_config=config,
        universe_codes=["600000"],
        bars_by_code={"600000": bars},
        calendar=calendar,
    )
    out = run_backtest(inp)
    assert len(out.equity) == 70
    # 发生过买入；末期权重应高于初始建仓比例（已加仓）
    buys = [t for t in out.trades if t.side == "buy"]
    assert len(buys) >= 2
    last_pos = [p for p in out.positions if p.trade_date == calendar[-1]]
    assert last_pos and float(last_pos[0].weight) > 0.4
