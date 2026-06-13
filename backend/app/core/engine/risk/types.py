"""风控引擎类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any, Optional


@dataclass
class RiskRuleDef:
    type: str
    params: dict[str, Any] = field(default_factory=dict)
    action: str = "reject"
    enabled: bool = True


@dataclass
class OrderIntent:
    code: str
    side: str
    qty: int
    price: float
    order_type: str = "limit"


@dataclass
class PositionSnapshot:
    code: str
    qty: int
    avail_qty: int
    market_value: float


@dataclass
class RiskContext:
    portfolio_id: int
    user_id: int
    cash: float
    total_value: float
    positions: list[PositionSnapshot]
    trade_date: date
    daily_order_amount: float = 0.0
    is_st_codes: set[str] = field(default_factory=set)
    suspended_codes: set[str] = field(default_factory=set)


@dataclass
class RiskDecision:
    allow: bool
    adjusted_qty: Optional[int] = None
    rule: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
