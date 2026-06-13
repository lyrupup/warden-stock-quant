"""M4 回测 Pydantic 模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field

from app.features.strategies.schema import Universe


class BacktestCreate(BaseModel):
    name: Optional[str] = None
    strategy_version_id: int
    params: Optional[dict[str, Any]] = None
    universe: Optional[Universe] = None
    date_from: date
    date_to: date
    init_capital: Decimal = Field(..., gt=0)
    benchmark: str = "000300"
    adjust: str = "qfq"
    cost_config: Optional[dict[str, Any]] = None


class BacktestView(BaseModel):
    id: int
    name: Optional[str] = None
    status: str
    progress: Decimal
    job_id: Optional[str] = None
    strategy_version_id: int
    # 关联策略信息（基于 strategy_version_id 反查；策略被删除时为空）
    strategy_id: Optional[int] = None
    strategy_name: Optional[str] = None
    strategy_version: Optional[int] = None
    date_from: date
    date_to: date
    init_capital: Decimal
    benchmark: str
    adjust: str
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class BacktestStrategyView(BaseModel):
    """回测当时绑定的策略版本快照（不可变）。"""

    strategy_version_id: int
    strategy_id: Optional[int] = None
    strategy_name: Optional[str] = None
    version: Optional[int] = None
    type: Optional[str] = None
    description: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    universe: Optional[dict[str, Any]] = None
    params: Optional[dict[str, Any]] = None
    created_at: Optional[datetime] = None


class BacktestMetricsView(BaseModel):
    total_return: Optional[Decimal] = None
    annual_return: Optional[Decimal] = None
    volatility: Optional[Decimal] = None
    sharpe: Optional[Decimal] = None
    sortino: Optional[Decimal] = None
    calmar: Optional[Decimal] = None
    max_drawdown: Optional[Decimal] = None
    mdd_from: Optional[date] = None
    mdd_to: Optional[date] = None
    win_rate: Optional[Decimal] = None
    profit_factor: Optional[Decimal] = None
    turnover: Optional[Decimal] = None
    alpha: Optional[Decimal] = None
    beta: Optional[Decimal] = None
    info_ratio: Optional[Decimal] = None


class EquityPointView(BaseModel):
    trade_date: date
    nav: Optional[Decimal] = None
    benchmark_nav: Optional[Decimal] = None
    drawdown: Optional[Decimal] = None


class TradeView(BaseModel):
    id: int
    trade_date: date
    code: str
    side: str
    price: Optional[Decimal] = None
    qty: int
    amount: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    pnl: Optional[Decimal] = None


class PositionView(BaseModel):
    trade_date: date
    code: str
    qty: int
    price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    weight: Optional[Decimal] = None


class OptimizationCreate(BaseModel):
    name: Optional[str] = None
    strategy_version_id: int
    # 参数空间：{"fast": [3,5,8], "slow": [15,20,30]}
    param_space: dict[str, list[Any]] = Field(..., min_length=1)
    method: str = "grid"  # grid | random
    n_iter: int = Field(20, ge=1, le=500)
    objective: str = "sharpe"
    oos_split: float = Field(0.0, ge=0.0, le=0.8)
    universe: Optional[Universe] = None
    date_from: date
    date_to: date
    init_capital: Decimal = Field(..., gt=0)
    benchmark: str = "000300"
    adjust: str = "qfq"
    cost_config: Optional[dict[str, Any]] = None


class OptimizationView(BaseModel):
    id: int
    name: Optional[str] = None
    status: str
    progress: Decimal
    job_id: Optional[str] = None
    strategy_version_id: int
    strategy_name: Optional[str] = None
    strategy_version: Optional[int] = None
    method: str
    objective: str
    oos_split: Decimal
    total_combos: int
    param_space: dict[str, Any]
    date_from: date
    date_to: date
    init_capital: Decimal
    benchmark: str
    adjust: str
    summary: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    created_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


class OptimizationResultView(BaseModel):
    id: int
    params: dict[str, Any]
    objective_value: Optional[Decimal] = None
    is_metrics: Optional[dict[str, Any]] = None
    oos_metrics: Optional[dict[str, Any]] = None
    rank: Optional[int] = None

    model_config = {"from_attributes": True}
