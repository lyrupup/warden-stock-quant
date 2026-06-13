"""M6 因子 Pydantic 模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, Field


class FactorUpsert(BaseModel):
    name: str
    category: Optional[str] = None
    type: str = Field(default="builtin", pattern="^(expr|code|builtin)$")
    expr: Optional[str] = None
    code: Optional[str] = None
    params: Optional[dict[str, Any]] = None
    direction: int = Field(default=1, ge=-1, le=1)


class FactorView(FactorUpsert):
    id: int
    created_at: datetime


class FactorComputeRequest(BaseModel):
    universe: Optional[dict[str, Any]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class FactorAnalyzeRequest(BaseModel):
    forward_period: int = Field(default=5, ge=1, le=60)
    n_quantiles: int = Field(default=5, ge=2, le=20)
    neutralize: Optional[list[str]] = None
    universe: Optional[dict[str, Any]] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class FactorAnalysisView(BaseModel):
    id: int
    status: str
    forward_period: int
    n_quantiles: int
    ic_mean: Optional[Decimal] = None
    ic_ir: Optional[Decimal] = None
    ic_win_rate: Optional[Decimal] = None
    ic_series: Optional[list[dict[str, Any]]] = None
    quantile_returns: Optional[dict[str, Any]] = None
    turnover: Optional[dict[str, Any]] = None
    job_id: Optional[str] = None
    created_at: Optional[datetime] = None


class FactorCombineRequest(BaseModel):
    name: str
    members: list[dict[str, Any]]
    scheme: str = Field(default="equal", pattern="^(equal|ic_weight|regression)$")
    neutralize: Optional[list[str]] = None
