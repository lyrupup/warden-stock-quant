"""PaperGateway：仿真撮合（与回测成本口径一致）。"""

from __future__ import annotations

from decimal import Decimal

from app.core.engine.backtest.cost import apply_slippage, calc_commission, calc_sell_tax, round_lot
from app.core.engine.backtest.types import CostModel
from app.core.engine.execution.types import FillResult
from app.core.engine.risk.types import OrderIntent


class PaperGateway:
    """纸面交易网关：即时按限价/市价（收盘价）全额成交。"""

    def __init__(self, cost: CostModel | None = None) -> None:
        self._cost = cost or CostModel()

    def fill(
        self,
        order: OrderIntent,
        *,
        cash: Decimal,
        avail_qty: int,
    ) -> FillResult:
        qty = round_lot(order.qty)
        if qty <= 0:
            return FillResult(0, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), False, "数量须为 100 股整数倍")

        raw_price = order.price
        fill_price = Decimal(str(round(apply_slippage(raw_price, order.side, self._cost), 4)))
        amount = fill_price * qty
        commission = Decimal(str(round(calc_commission(float(amount), self._cost), 4)))
        tax = Decimal("0")
        if order.side == "sell":
            if qty > avail_qty:
                return FillResult(0, fill_price, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), False, "可卖数量不足")
            tax = Decimal(str(round(calc_sell_tax(float(amount), self._cost), 4)))
            cash_delta = amount - commission - tax
        else:
            total_cost = amount + commission
            if total_cost > cash:
                return FillResult(0, fill_price, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"), False, "可用资金不足")
            cash_delta = -(amount + commission)

        return FillResult(
            filled_qty=qty,
            fill_price=fill_price,
            amount=amount,
            commission=commission,
            tax=tax,
            cash_delta=cash_delta,
            success=True,
        )
