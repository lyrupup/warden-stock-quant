"""M5 绩效分析引擎单测。"""

from __future__ import annotations

from datetime import date, timedelta

from app.core.engine.report.analysis import (
    build_report_analysis,
    compute_benchmark_metrics,
    compute_monthly_returns,
    compute_rolling_sharpe,
    compute_stock_attribution,
)


def _equity_points(n: int = 120, start: date = date(2024, 1, 2)):
    rows = []
    nav = 1_000_000.0
    bench = 1_000_000.0
    peak = nav
    for i in range(n):
        d = start + timedelta(days=i)
        nav *= 1.001 if i % 5 else 0.998
        bench *= 1.0005
        peak = max(peak, nav)
        dd = (nav - peak) / peak
        rows.append(
            {
                "trade_date": d,
                "nav": nav,
                "benchmark_nav": bench,
                "drawdown": dd,
            }
        )
    return rows


def test_monthly_returns_groups_by_calendar_month():
    equity = _equity_points(90)
    monthly = compute_monthly_returns(equity)
    assert len(monthly) >= 2
    assert "year" in monthly[0] and "month" in monthly[0] and "return" in monthly[0]


def test_benchmark_metrics_alpha_beta_ir():
    equity = _equity_points(100)
    m = compute_benchmark_metrics(equity)
    assert m["beta"] is not None
    assert m["alpha"] is not None
    assert m["info_ratio"] is not None


def test_rolling_sharpe_has_values_after_warmup():
    equity = _equity_points(80)
    rolling = compute_rolling_sharpe(equity, window=20)
    assert len(rolling) == len(equity)
    assert any(r["sharpe"] is not None for r in rolling[25:])


def test_stock_attribution_from_sell_trades():
    trades = [
        {"code": "600000", "side": "sell", "pnl": 1000.0},
        {"code": "600000", "side": "sell", "pnl": -200.0},
        {"code": "000001", "side": "sell", "pnl": 500.0},
        {"code": "600000", "side": "buy", "pnl": None},
    ]
    attr = compute_stock_attribution(trades)
    assert len(attr) == 2
    assert attr[0]["code"] == "600000"
    assert attr[0]["total_pnl"] == 800.0


def test_build_report_analysis_bundle():
    equity = _equity_points(60)
    trades = [{"code": "600000", "side": "sell", "pnl": 100.0, "trade_date": date(2024, 2, 1)}]
    positions = [{"trade_date": date(2024, 1, 10), "code": "600000", "weight": 0.8}]
    report = build_report_analysis(equity, trades, positions)
    assert "monthly_returns" in report
    assert "rolling_sharpe" in report
    assert "benchmark_metrics" in report
    assert "stock_attribution" in report
    assert "concentration" in report
