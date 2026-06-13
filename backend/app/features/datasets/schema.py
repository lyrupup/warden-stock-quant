"""M2 数据集 API Schema。"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field


class DatasetStatusView(BaseModel):
    latest_trade_date: Optional[str] = None
    bars_updated_to: Optional[str] = None
    securities_count: int = 0
    gaps: list[str] = Field(default_factory=list)
    stale: bool = False


class SyncRequest(BaseModel):
    type: Literal["securities", "daily_bars", "indicators", "calendar"] = "securities"
    codes: Optional[list[str]] = None
    date_from: Optional[date] = None


class DataSourceCreate(BaseModel):
    name: Optional[str] = None
    base_url: str
    secret_id: str
    secret_key: str
    qps_limit: Optional[int] = None
    daily_quota: Optional[int] = None


class DataSourceView(BaseModel):
    id: int
    name: Optional[str]
    base_url: str
    secret_id: str
    qps_limit: Optional[int]
    daily_quota: Optional[int]
    enabled: bool


class JobView(BaseModel):
    id: str
    type: str
    ref_id: Optional[int]
    status: str
    progress: str
    result: Optional[dict] = None
    error: Optional[str] = None
