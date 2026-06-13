"""M8 交易 Pydantic 模型。"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class OrderCreate(BaseModel):
    code: str
    side: str = Field(..., pattern="^(buy|sell)$")
    order_type: str = Field(default="limit", pattern="^(limit|market)$")
    price: Optional[float] = None
    qty: int = Field(..., gt=0)


class OrderView(BaseModel):
    id: int
    code: str
    side: str
    order_type: str
    price: Optional[Decimal] = None
    qty: int
    filled_qty: int
    status: str
    gateway: str
    reason: Optional[str] = None
    trade_date: Optional[date] = None
    created_at: datetime


class TradeView(BaseModel):
    id: int
    order_id: int
    code: str
    side: str
    price: Optional[Decimal] = None
    qty: int
    amount: Optional[Decimal] = None
    commission: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    trade_time: datetime


class SignalView(BaseModel):
    code: str
    side: str
    qty: int
    price: float
    reason: str
