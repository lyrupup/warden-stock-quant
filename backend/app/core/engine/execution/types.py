"""Paper 仿真撮合结果。"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class FillResult:
    filled_qty: int
    fill_price: Decimal
    amount: Decimal
    commission: Decimal
    tax: Decimal
    cash_delta: Decimal
    success: bool
    reason: str = ""
