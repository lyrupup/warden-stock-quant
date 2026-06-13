"""M5 绩效分析引擎。"""

from app.core.engine.report.analysis import (
    build_report_analysis,
    compute_benchmark_metrics,
    compute_monthly_returns,
    compute_return_distribution,
    compute_rolling_sharpe,
    compute_stock_attribution,
)

__all__ = [
    "build_report_analysis",
    "compute_benchmark_metrics",
    "compute_monthly_returns",
    "compute_return_distribution",
    "compute_rolling_sharpe",
    "compute_stock_attribution",
]
