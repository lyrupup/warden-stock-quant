"""M9 风控 Pydantic 模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class RiskRuleItem(BaseModel):
    type: str
    params: Optional[dict[str, Any]] = None
    action: str = Field(default="reject", pattern="^(reject|alert|liquidate)$")
    enabled: bool = True


class RiskRuleSetUpsert(BaseModel):
    name: str
    scope: str = Field(default="portfolio", pattern="^(portfolio|account)$")
    rules: list[RiskRuleItem] = Field(default_factory=list)


class RiskRuleSetView(RiskRuleSetUpsert):
    id: int
    is_platform: bool = False
    created_at: datetime


class RiskEventView(BaseModel):
    id: int
    portfolio_id: Optional[int] = None
    order_id: Optional[int] = None
    rule_type: str
    action: str
    detail: Optional[dict[str, Any]] = None
    created_at: datetime
