"""交易成本计算。"""

from __future__ import annotations

from app.core.engine.backtest.types import CostModel


def apply_slippage(price: float, side: str, cost: CostModel) -> float:
    """按配置对成交价施加滑点。"""
    if cost.slippage_type == "none" or cost.slippage_value <= 0:
        return price
    if cost.slippage_type == "pct":
        adj = price * cost.slippage_value
        return price + adj if side == "buy" else price - adj
    return price


def calc_commission(amount: float, cost: CostModel) -> float:
    """买卖佣金（双边），取 rate 与最低佣金较大值。"""
    fee = amount * cost.commission_rate
    transfer = amount * cost.transfer_fee_rate
    return max(fee, cost.commission_min) + transfer


def calc_sell_tax(amount: float, cost: CostModel) -> float:
    """卖出印花税（单边）。"""
    return amount * cost.stamp_tax_rate


def round_lot(qty: int, lot: int = 100) -> int:
    """A 股买入向下取整到最小交易单位。"""
    if qty <= 0:
        return 0
    return (qty // lot) * lot
