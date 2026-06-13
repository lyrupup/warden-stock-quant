"""M5 绩效报告 Pydantic 模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.features.backtests.schema import BacktestMetricsView, BacktestView


class BenchmarkMetricsView(BaseModel):
    alpha: Optional[float] = None
    beta: Optional[float] = None
    info_ratio: Optional[float] = None


class MonthlyReturnView(BaseModel):
    year: int
    month: int
    return_: float = Field(alias="return")

    model_config = {"populate_by_name": True}


class DrawdownPointView(BaseModel):
    trade_date: date
    drawdown: Optional[float] = None


class RollingSharpePointView(BaseModel):
    trade_date: date
    sharpe: Optional[float] = None


class ReturnDistBinView(BaseModel):
    bin_start: float
    bin_end: float
    count: int


class StockAttributionView(BaseModel):
    code: str
    total_pnl: float
    trade_count: int


class ConcentrationView(BaseModel):
    avg_max_weight: Optional[float] = None
    avg_holdings: Optional[float] = None


class ReportAnalysisView(BaseModel):
    benchmark_metrics: BenchmarkMetricsView
    monthly_returns: list[MonthlyReturnView]
    drawdown_series: list[DrawdownPointView]
    rolling_sharpe: list[RollingSharpePointView]
    return_distribution: list[ReturnDistBinView]
    stock_attribution: list[StockAttributionView]
    concentration: ConcentrationView


class BacktestReportView(BaseModel):
    backtest: BacktestView
    metrics: BacktestMetricsView
    analysis: ReportAnalysisView


class CompareBacktestsRequest(BaseModel):
    backtest_ids: list[int] = Field(..., min_length=2, max_length=10)


class CompareRowView(BaseModel):
    backtest_id: int
    name: Optional[str] = None
    strategy_name: Optional[str] = None
    strategy_version: Optional[int] = None
    date_from: date
    date_to: date
    metrics: BacktestMetricsView
    benchmark_metrics: BenchmarkMetricsView


class CompareReportView(BaseModel):
    rows: list[CompareRowView]


class ShareLinkRequest(BaseModel):
    expires_in: int = Field(default=86400, ge=60, le=604800)


class ShareLinkView(BaseModel):
    url: str
    token: str
    expires_at: datetime
