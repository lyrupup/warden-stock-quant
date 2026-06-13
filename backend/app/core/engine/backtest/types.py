"""回测引擎类型定义。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Callable, Optional


@dataclass
class CostModel:
    """A 股交易成本模型（佣金/印花税/滑点）。"""

    commission_rate: float = 0.0003
    commission_min: float = 5.0
    stamp_tax_rate: float = 0.0005
    transfer_fee_rate: float = 0.00001
    slippage_type: str = "pct"
    slippage_value: float = 0.0005

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> "CostModel":
        if not data:
            return cls()
        return cls(
            commission_rate=float(data.get("commission_rate", 0.0003)),
            commission_min=float(data.get("commission_min", 5.0)),
            stamp_tax_rate=float(data.get("stamp_tax_rate", 0.0005)),
            transfer_fee_rate=float(data.get("transfer_fee_rate", 0.00001)),
            slippage_type=str(data.get("slippage_type", "pct")),
            slippage_value=float(data.get("slippage_value", 0.0005)),
        )


@dataclass
class BarData:
    """单标的日 K 序列（已按日期升序）。"""

    code: str
    dates: list[date]
    open: list[float]
    high: list[float]
    low: list[float]
    close: list[float]
    suspended: list[bool]
    limit_up: list[Optional[float]]
    limit_down: list[Optional[float]]


@dataclass
class TradeRecord:
    trade_date: date
    code: str
    side: str  # buy | sell
    price: float
    qty: int
    amount: float
    commission: float
    tax: float
    pnl: Optional[float] = None


@dataclass
class PositionSnapshot:
    trade_date: date
    code: str
    qty: int
    price: float
    market_value: float
    weight: float


@dataclass
class EquityPoint:
    trade_date: date
    nav: float
    benchmark_nav: Optional[float]
    drawdown: float
    cash: float
    market_value: float


@dataclass
class BacktestEngineInput:
    """引擎纯逻辑输入（不依赖 DB）。"""

    date_from: date
    date_to: date
    init_capital: float
    adjust: str
    cost: CostModel
    strategy_config: dict[str, Any]
    universe_codes: list[str]
    params: dict[str, Any] = field(default_factory=dict)
    benchmark_bars: Optional[BarData] = None
    bars_by_code: dict[str, BarData] = field(default_factory=dict)
    calendar: list[date] = field(default_factory=list)


@dataclass
class BacktestEngineOutput:
    equity: list[EquityPoint]
    trades: list[TradeRecord]
    positions: list[PositionSnapshot]
    metrics: dict[str, Any]


ProgressCallback = Callable[[float], None]
CancelCallback = Callable[[], bool]
