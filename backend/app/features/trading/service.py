"""M8 仿真交易业务编排。"""

from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.data.feed.pg_feed import PgDataFeed
from app.core.engine.backtest.cost import round_lot
from app.core.engine.execution import PaperGateway
from app.core.engine.risk import OrderIntent, PositionSnapshot, RiskContext
from app.core.errors import NotFoundError, RiskRejectedError, ValidationFailedError
from app.features.datasets.models import MarketDailyBar, MarketSecurity
from app.features.portfolios.models import Portfolio, Position
from app.features.portfolios.repository import PortfolioRepository
from app.features.risk.service import RiskService
from app.features.trading.models import Order, Trade
from app.features.trading.repository import TradingRepository
from app.features.trading.schema import OrderCreate, OrderView, SignalView, TradeView


class TradingService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TradingRepository(session)
        self._portfolio_repo = PortfolioRepository(session)
        self._risk_svc = RiskService(session)
        self._gateway = PaperGateway()

    async def list_orders(
        self, user_id: int, portfolio_id: int, page: int, size: int
    ) -> tuple[list[dict], int]:
        await self._require_portfolio(portfolio_id, user_id)
        rows, total = await self._repo.list_orders(portfolio_id, page, size)
        return [OrderView.model_validate(r, from_attributes=True).model_dump() for r in rows], total

    async def list_trades(
        self, user_id: int, portfolio_id: int, page: int, size: int
    ) -> tuple[list[dict], int]:
        await self._require_portfolio(portfolio_id, user_id)
        rows, total = await self._repo.list_trades(portfolio_id, page, size)
        return [TradeView.model_validate(r, from_attributes=True).model_dump() for r in rows], total

    async def submit_order(
        self, user_id: int, portfolio_id: int, payload: OrderCreate
    ) -> dict:
        portfolio = await self._require_portfolio(portfolio_id, user_id)
        if portfolio.mode != "paper":
            raise ValidationFailedError("当前仅支持 Paper 仿真下单")

        trade_date = await self._latest_trade_date()
        price = await self._resolve_price(payload.code, payload.price, payload.order_type, trade_date)
        qty = round_lot(payload.qty)
        if qty <= 0:
            raise ValidationFailedError("数量须为 100 股整数倍")

        order = Order(
            user_id=user_id,
            portfolio_id=portfolio_id,
            code=payload.code,
            side=payload.side,
            order_type=payload.order_type,
            price=Decimal(str(round(price, 4))),
            qty=qty,
            status="created",
            gateway="paper",
            trade_date=trade_date,
        )
        await self._repo.add_order(order)

        ctx = await self._build_risk_context(portfolio, trade_date)
        engine = await self._risk_svc.load_engine_for_portfolio(user_id, portfolio.risk_rule_set_id)
        intent = OrderIntent(
            code=payload.code,
            side=payload.side,
            qty=qty,
            price=price,
            order_type=payload.order_type,
        )
        decision = engine.check_order(intent, ctx)
        if not decision.allow:
            order.status = "risk_rejected"
            order.reason = decision.reason
            await self._risk_svc.record_rejection(
                user_id,
                portfolio_id,
                order.id,
                decision.rule or "unknown",
                decision.action or "reject",
                decision.reason or "风控拦截",
            )
            await self._session.flush()
            await self._session.commit()
            raise RiskRejectedError(decision.reason or "风控拦截")

        exec_qty = decision.adjusted_qty or qty
        intent.qty = exec_qty
        pos = await self._get_position(portfolio_id, payload.code)
        avail = pos.avail_qty if pos else 0
        fill = self._gateway.fill(intent, cash=portfolio.cash, avail_qty=avail)
        if not fill.success:
            order.status = "rejected"
            order.reason = fill.reason
            await self._session.flush()
            raise ValidationFailedError(fill.reason)

        order.status = "filled"
        order.filled_qty = fill.filled_qty
        order.price = fill.fill_price

        trade = Trade(
            order_id=order.id,
            portfolio_id=portfolio_id,
            code=payload.code,
            side=payload.side,
            price=fill.fill_price,
            qty=fill.filled_qty,
            amount=fill.amount,
            commission=fill.commission,
            tax=fill.tax,
        )
        await self._repo.add_trade(trade)
        await self._apply_fill(portfolio, portfolio_id, payload.code, payload.side, fill)
        await self._session.flush()
        return OrderView.model_validate(order, from_attributes=True).model_dump()

    async def cancel_order(self, user_id: int, order_id: int) -> dict:
        order = await self._repo.get_order(order_id, user_id)
        if order is None:
            raise NotFoundError("订单不存在")
        if order.status in ("filled", "canceled", "risk_rejected"):
            raise ValidationFailedError(f"订单状态 {order.status} 不可撤单")
        order.status = "canceled"
        await self._session.flush()
        return OrderView.model_validate(order, from_attributes=True).model_dump()

    async def list_signals(self, user_id: int, portfolio_id: int) -> list[dict]:
        """调仓信号建议：对比目标仓位与当前持仓，不实际下单。"""
        from app.features.portfolios.service import PortfolioService

        portfolio = await self._require_portfolio(portfolio_id, user_id)
        if not portfolio.strategy_version_id:
            return []
        preview = await PortfolioService(self._session)._compute_rebalance_targets(
            user_id, portfolio_id
        )
        signals: list[dict] = []
        positions = {p.code: p for p in await self._portfolio_repo.list_positions(portfolio_id)}
        for t in preview.get("targets", []):
            code = t["code"]
            target_qty = int(t.get("target_qty", 0))
            cur = positions.get(code)
            cur_qty = cur.qty if cur else 0
            diff = target_qty - cur_qty
            if diff > 0:
                signals.append(
                    SignalView(
                        code=code,
                        side="buy",
                        qty=diff,
                        price=float(t.get("price", 0)),
                        reason="再平衡增仓",
                    ).model_dump()
                )
            elif diff < 0:
                signals.append(
                    SignalView(
                        code=code,
                        side="sell",
                        qty=-diff,
                        price=float(t.get("price", 0)),
                        reason="再平衡减仓",
                    ).model_dump()
                )
        for code, pos in positions.items():
            if code not in {t["code"] for t in preview.get("targets", [])} and pos.qty > 0:
                signals.append(
                    SignalView(
                        code=code,
                        side="sell",
                        qty=pos.avail_qty or pos.qty,
                        price=float(pos.last_price or 0),
                        reason="移出组合",
                    ).model_dump()
                )
        return signals

    async def _build_risk_context(self, portfolio: Portfolio, trade_date: date) -> RiskContext:
        positions = await self._portfolio_repo.list_positions(portfolio.id)
        pos_snaps = [
            PositionSnapshot(
                code=p.code,
                qty=p.qty,
                avail_qty=p.avail_qty,
                market_value=float(p.market_value or 0),
            )
            for p in positions
        ]
        total_mv = sum(s.market_value for s in pos_snaps)
        total_value = float(portfolio.cash) + total_mv
        st_codes = set(
            (
                await self._session.execute(
                    select(MarketSecurity.code).where(MarketSecurity.is_st.is_(True))
                )
            )
            .scalars()
            .all()
        )
        suspended = set(
            (
                await self._session.execute(
                    select(MarketDailyBar.code).where(
                        MarketDailyBar.trade_date == trade_date,
                        MarketDailyBar.suspended.is_(True),
                    )
                )
            )
            .scalars()
            .all()
        )
        daily_amt = await self._repo.sum_daily_amount(portfolio.id, trade_date)
        return RiskContext(
            portfolio_id=portfolio.id,
            user_id=portfolio.user_id,
            cash=float(portfolio.cash),
            total_value=total_value,
            positions=pos_snaps,
            trade_date=trade_date,
            daily_order_amount=daily_amt,
            is_st_codes=st_codes,
            suspended_codes=suspended,
        )

    async def _apply_fill(self, portfolio: Portfolio, portfolio_id: int, code: str, side: str, fill) -> None:
        portfolio.cash = portfolio.cash + fill.cash_delta
        pos = await self._get_position(portfolio_id, code)
        if side == "buy":
            if pos is None:
                await self._portfolio_repo.upsert_position(
                    portfolio_id,
                    code,
                    qty=fill.filled_qty,
                    avail_qty=0,
                    cost=fill.amount,
                    last_price=fill.fill_price,
                    market_value=fill.amount,
                    pnl=Decimal("0"),
                )
            else:
                new_qty = pos.qty + fill.filled_qty
                new_cost = (pos.cost or Decimal("0")) + fill.amount
                await self._portfolio_repo.upsert_position(
                    portfolio_id,
                    code,
                    qty=new_qty,
                    avail_qty=pos.avail_qty,
                    cost=new_cost,
                    last_price=fill.fill_price,
                    market_value=fill.fill_price * new_qty,
                    pnl=pos.pnl,
                )
        else:
            if pos is None:
                return
            new_qty = pos.qty - fill.filled_qty
            if new_qty <= 0:
                new_qty = 0
            await self._portfolio_repo.upsert_position(
                portfolio_id,
                code,
                qty=new_qty,
                avail_qty=min(pos.avail_qty, new_qty),
                cost=pos.cost,
                last_price=fill.fill_price,
                market_value=fill.fill_price * new_qty if new_qty else Decimal("0"),
                pnl=(pos.pnl or Decimal("0")) + fill.cash_delta,
            )

    async def _get_position(self, portfolio_id: int, code: str) -> Optional[Position]:
        rows = await self._portfolio_repo.list_positions(portfolio_id)
        return next((p for p in rows if p.code == code), None)

    async def _resolve_price(
        self, code: str, price: Optional[float], order_type: str, trade_date: date
    ) -> float:
        if order_type == "limit":
            if price is None or price <= 0:
                raise ValidationFailedError("限价单须指定 price")
            return float(price)
        row = (
            await self._session.execute(
                select(MarketDailyBar.close).where(
                    MarketDailyBar.code == code, MarketDailyBar.trade_date == trade_date
                )
            )
        ).scalar_one_or_none()
        if row is None:
            raise ValidationFailedError(f"无法获取 {code} 在 {trade_date} 的行情价")
        return float(row)

    async def _latest_trade_date(self) -> date:
        feed = PgDataFeed(self._session)
        status = await feed.dataset_status()
        latest_str = status.get("bars_updated_to") or status.get("latest_trade_date")
        if not latest_str:
            raise ValidationFailedError("数据集为空")
        return date.fromisoformat(latest_str)

    async def _require_portfolio(self, portfolio_id: int, user_id: int) -> Portfolio:
        p = await self._portfolio_repo.get_owned(portfolio_id, user_id)
        if p is None:
            raise NotFoundError("组合不存在")
        return p
