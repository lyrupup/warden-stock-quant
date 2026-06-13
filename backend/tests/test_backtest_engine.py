"""回测引擎单元测试（纯逻辑，不依赖 DB）。"""

from __future__ import annotations

from datetime import date, timedelta

from app.core.engine.backtest.cost import calc_commission, round_lot
from app.core.engine.backtest.simulator import run_backtest
from app.core.engine.backtest.types import BacktestEngineInput, BarData, CostModel


def _trend_bars(code: str, start: date, n: int, base: float = 10.0) -> BarData:
    dates = [start + timedelta(days=i) for i in range(n)]
    closes = [base + i * 0.5 for i in range(n)]
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


def test_round_lot_and_commission():
    assert round_lot(150) == 100
    assert round_lot(99) == 0
    fee = calc_commission(10000, CostModel())
    assert fee >= 5.0


def test_ma_cross_backtest_produces_equity_and_metrics():
    start = date(2024, 1, 2)
    n = 60
    calendar = [start + timedelta(days=i) for i in range(n)]
    bars = _trend_bars("600000", start, n)
    inp = BacktestEngineInput(
        date_from=start,
        date_to=start + timedelta(days=n - 1),
        init_capital=1_000_000.0,
        adjust="qfq",
        cost=CostModel(),
        strategy_config={
            "signals": [{"type": "ma_cross", "fast": 5, "slow": 10}],
            "rebalance": {"freq": "day"},
            "position": {"scheme": "equal_weight", "max_n": 1},
            "stop": {"stop_loss": 0.2},
        },
        universe_codes=["600000"],
        bars_by_code={"600000": bars},
        calendar=calendar,
    )
    out = run_backtest(inp)
    assert len(out.equity) == n
    assert out.equity[-1].nav > 0
    assert "total_return" in out.metrics
    assert out.metrics["max_drawdown"] <= 0
