"""风控规则引擎（回测/仿真/实盘共用）。"""

from __future__ import annotations

from app.core.engine.backtest.cost import round_lot
from app.core.engine.risk.types import OrderIntent, RiskContext, RiskDecision, RiskRuleDef


class RiskEngine:
    """事前风控：对单笔下单意图逐条规则校验。"""

    def __init__(self, rules: list[RiskRuleDef]) -> None:
        self._rules = [r for r in rules if r.enabled]

    def check_order(self, order: OrderIntent, ctx: RiskContext) -> RiskDecision:
        qty = order.qty
        for rule in self._rules:
            decision = self._apply_rule(rule, order, ctx, qty)
            if not decision.allow:
                return decision
            if decision.adjusted_qty is not None:
                qty = decision.adjusted_qty
        if qty <= 0:
            return RiskDecision(allow=False, rule="qty", reason="有效数量为 0")
        if qty != order.qty:
            return RiskDecision(allow=True, adjusted_qty=qty)
        return RiskDecision(allow=True)

    def _apply_rule(
        self, rule: RiskRuleDef, order: OrderIntent, ctx: RiskContext, qty: int
    ) -> RiskDecision:
        rtype = rule.type
        params = rule.params or {}

        if rtype == "blacklist":
            codes = set(params.get("codes") or [])
            if order.code in codes:
                return self._reject(rule, f"标的 {order.code} 在黑名单中")

        if rtype == "whitelist":
            codes = set(params.get("codes") or [])
            if codes and order.code not in codes:
                return self._reject(rule, f"标的 {order.code} 不在白名单")

        if rtype == "no_st" and order.code in ctx.is_st_codes:
            return self._reject(rule, f"禁止买入 ST 标的 {order.code}")

        if rtype == "tradable" and order.code in ctx.suspended_codes:
            return self._reject(rule, f"标的 {order.code} 停牌不可交易")

        if rtype == "max_order_amount":
            limit = float(params.get("max", 0))
            amount = qty * order.price
            if limit > 0 and amount > limit:
                max_qty = round_lot(int(limit / order.price))
                if max_qty <= 0:
                    return self._reject(rule, "单笔金额超限")
                if rule.action == "reject":
                    return self._reject(rule, "单笔金额超限")
                return RiskDecision(
                    allow=True,
                    adjusted_qty=max_qty,
                    rule=rtype,
                    reason=f"单笔金额超限，削减至 {max_qty} 股",
                )

        if rtype == "max_daily_amount":
            limit = float(params.get("max", 0))
            amount = qty * order.price
            if limit > 0 and ctx.daily_order_amount + amount > limit:
                remain = max(0.0, limit - ctx.daily_order_amount)
                max_qty = round_lot(int(remain / order.price))
                if max_qty <= 0:
                    return self._reject(rule, "单日下单金额已达上限")
                if rule.action == "reject":
                    return self._reject(rule, "单日下单金额已达上限")
                return RiskDecision(
                    allow=True,
                    adjusted_qty=max_qty,
                    rule=rtype,
                    reason=f"单日金额超限，削减至 {max_qty} 股",
                )

        if rtype == "max_position_pct" and ctx.total_value > 0:
            pct = float(params.get("max_pct", params.get("max", 0.2)))
            pos = next((p for p in ctx.positions if p.code == order.code), None)
            cur_mv = pos.market_value if pos else 0.0
            if order.side == "buy":
                new_mv = cur_mv + qty * order.price
                if new_mv / ctx.total_value > pct:
                    allowed_mv = pct * ctx.total_value - cur_mv
                    max_qty = round_lot(int(allowed_mv / order.price)) if order.price > 0 else 0
                    if max_qty <= 0:
                        return self._reject(rule, f"单票仓位超过 {pct:.0%} 上限")
                    if rule.action == "reject":
                        return self._reject(rule, f"单票仓位超过 {pct:.0%} 上限")
                    return RiskDecision(
                        allow=True,
                        adjusted_qty=max_qty,
                        rule=rtype,
                        reason=f"单票仓位上限 {pct:.0%}，削减至 {max_qty} 股",
                    )

        if rtype == "max_count" and order.side == "buy":
            max_n = int(params.get("max", 10))
            held = {p.code for p in ctx.positions if p.qty > 0}
            if order.code not in held and len(held) >= max_n:
                return self._reject(rule, f"持仓只数已达上限 {max_n}")

        if order.side == "sell":
            pos = next((p for p in ctx.positions if p.code == order.code), None)
            avail = pos.avail_qty if pos else 0
            if qty > avail:
                if avail <= 0:
                    return self._reject(rule, "可用卖出数量不足（T+1）")
                return RiskDecision(
                    allow=True,
                    adjusted_qty=avail,
                    rule="avail_qty",
                    reason=f"可卖 {avail} 股",
                )

        if order.side == "buy":
            amount = qty * order.price
            if amount > ctx.cash:
                max_qty = round_lot(int(ctx.cash / order.price)) if order.price > 0 else 0
                if max_qty <= 0:
                    return self._reject(rule, "可用资金不足")
                return RiskDecision(
                    allow=True,
                    adjusted_qty=max_qty,
                    rule="cash",
                    reason=f"资金不足，削减至 {max_qty} 股",
                )

        return RiskDecision(allow=True)

    def _reject(self, rule: RiskRuleDef, reason: str) -> RiskDecision:
        return RiskDecision(
            allow=False,
            rule=rule.type,
            action=rule.action,
            reason=reason,
        )
