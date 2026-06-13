"""M7 组合 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class PortfolioUpsert(BaseModel):
    name: str
    mode: str = Field(default="paper", pattern="^(paper|live)$")
    strategy_version_id: Optional[int] = None
    init_capital: float = Field(..., gt=0)
    benchmark: str = "000300"
    rebalance: str = Field(default="week", pattern="^(day|week|month)$")
    weight_scheme: Optional[dict[str, Any]] = None
    risk_rule_set_id: Optional[int] = None


class PortfolioView(PortfolioUpsert):
    id: int
    cash: Decimal
    status: str = "active"
    created_at: datetime


class PositionView(BaseModel):
    id: int
    code: str
    qty: int
    avail_qty: int
    cost: Optional[Decimal] = None
    last_price: Optional[Decimal] = None
    market_value: Optional[Decimal] = None
    pnl: Optional[Decimal] = None
    updated_at: datetime


class RebalanceResultView(BaseModel):
    trade_date: str
    targets: list[dict[str, Any]]
    orders: list[dict[str, Any]]
    message: str
