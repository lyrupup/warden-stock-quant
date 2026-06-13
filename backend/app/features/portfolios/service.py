"""M7 组合业务编排。"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.engine.backtest.compiler import ConfigStrategyCompiler
from app.core.engine.backtest.data_loader import bar_row_to_data, resolve_universe_codes
from app.core.engine.backtest.signals import compute_factor_rank_states, compute_hold_states
from app.core.engine.factor.compute import compute_factor_matrix
from app.core.data.feed.pg_feed import PgDataFeed
from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.features.portfolios.models import Portfolio
from app.features.portfolios.repository import PortfolioRepository
from app.features.portfolios.schema import PortfolioUpsert, PortfolioView, PositionView, RebalanceResultView
from app.features.strategies.repository import StrategyRepository
from app.features.trading.schema import OrderCreate
from app.features.trading.service import TradingService


class PortfolioService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = PortfolioRepository(session)
        self._strategy_repo = StrategyRepository(session)

    def _to_view(self, p: Portfolio) -> dict:
        return PortfolioView(
            id=p.id,
            name=p.name,
            mode=p.mode,
            strategy_version_id=p.strategy_version_id,
            init_capital=p.init_capital,
            cash=p.cash,
            benchmark=p.benchmark,
            rebalance=p.rebalance,
            weight_scheme=p.weight_scheme,
            risk_rule_set_id=p.risk_rule_set_id,
            status=p.status,
            created_at=p.created_at,
        ).model_dump()

    async def list_portfolios(self, user_id: int, page: int, size: int) -> tuple[list[dict], int]:
        rows, total = await self._repo.list_by_user(user_id, page, size)
        return [self._to_view(r) for r in rows], total

    async def get_portfolio(self, user_id: int, portfolio_id: int) -> dict:
        p = await self._require_owned(portfolio_id, user_id)
        return self._to_view(p)

    async def create_portfolio(self, user_id: int, payload: PortfolioUpsert) -> dict:
        if payload.mode == "live":
            raise ForbiddenError("实盘组合需管理员授权")
        existing = await self._repo.get_by_name(user_id, payload.name)
        if existing:
            raise ConflictError("同名组合已存在")
        if payload.strategy_version_id:
            ver = await self._strategy_repo.get_version_owned(
                payload.strategy_version_id, user_id
            )
            if ver is None:
                raise NotFoundError("策略版本不存在")
        p = Portfolio(
            user_id=user_id,
            name=payload.name,
            mode=payload.mode,
            strategy_version_id=payload.strategy_version_id,
            init_capital=Decimal(str(payload.init_capital)),
            cash=Decimal(str(payload.init_capital)),
            benchmark=payload.benchmark,
            rebalance=payload.rebalance,
            weight_scheme=payload.weight_scheme,
            risk_rule_set_id=payload.risk_rule_set_id,
        )
        await self._repo.add(p)
        return self._to_view(p)

    async def delete_portfolio(self, user_id: int, portfolio_id: int) -> None:
        p = await self._require_owned(portfolio_id, user_id)
        await self._repo.delete(p)

    async def list_positions(self, user_id: int, portfolio_id: int) -> list[dict]:
        await self._require_owned(portfolio_id, user_id)
        rows = await self._repo.list_positions(portfolio_id)
        return [
            PositionView.model_validate(r, from_attributes=True).model_dump() for r in rows
        ]

    async def _compute_rebalance_targets(
        self, user_id: int, portfolio_id: int
    ) -> dict[str, Any]:
        """计算再平衡目标仓位（不下单）。"""
        p = await self._require_owned(portfolio_id, user_id)
        if not p.strategy_version_id:
            raise ValidationFailedError("组合未关联策略版本，无法再平衡")

        pair = await self._strategy_repo.get_version_owned(p.strategy_version_id, user_id)
        if pair is None:
            raise NotFoundError("策略版本不存在")
        _strategy, version = pair
        config = version.config or {}
        if not config:
            raise ValidationFailedError("策略配置为空")

        feed = PgDataFeed(self._session)
        status = await feed.dataset_status()
        latest_str = status.get("bars_updated_to") or status.get("latest_trade_date")
        if not latest_str:
            raise ValidationFailedError("交易日历为空，请先同步数据集")
        trade_date = date.fromisoformat(latest_str)

        universe = version.universe or {"type": "all"}
        codes = await resolve_universe_codes(self._session, universe, max_codes=50)
        warmup_start = trade_date.replace(year=trade_date.year - 1)
        bars_by_code = {}
        for code in codes:
            rows = await feed.get_bars(code, warmup_start, trade_date, adjust="qfq")
            if rows:
                bars_by_code[code] = bar_row_to_data(code, rows)
        if not bars_by_code:
            raise ValidationFailedError("无可用行情，无法再平衡")

        full_calendar = sorted({d for bars in bars_by_code.values() for d in bars.dates})
        compiler = ConfigStrategyCompiler(config, {})
        selected: list[str] = []

        if compiler.signal_type == "factor_rank":
            sig = compiler.primary_signal
            factor_name = str(sig.get("factor", "momentum_20"))
            top = float(sig.get("top", 0.1))
            matrix = compute_factor_matrix(
                bars_by_code, full_calendar, factor_name, version.default_params, 1
            )
            states = compute_factor_rank_states(sig, matrix, full_calendar, trade_date, top)
            selected = [c for c, hold in states.items() if hold]
        elif compiler.supported():
            states_full = compute_hold_states(
                compiler.primary_signal, {}, bars_by_code, full_calendar
            )
            cal_idx = full_calendar.index(trade_date)
            selected = [c for c, arr in states_full.items() if arr[cal_idx]]
        else:
            raise ValidationFailedError(f"暂不支持的策略信号: {compiler.signal_type}")

        max_n = compiler.max_n
        selected = selected[:max_n] if selected else list(bars_by_code.keys())[:max_n]
        if not selected:
            raise ValidationFailedError("未选出任何标的")

        weight = 1.0 / len(selected)
        positions = await self._repo.list_positions(portfolio_id)
        total_capital = float(p.cash) + sum(float(pos.market_value or 0) for pos in positions)
        targets: list[dict[str, Any]] = []

        for code in selected:
            bars = bars_by_code.get(code)
            if not bars:
                continue
            price_map = {d: bars.close[i] for i, d in enumerate(bars.dates)}
            price = price_map.get(trade_date, bars.close[-1])
            target_value = total_capital * weight
            qty = int(target_value / price / 100) * 100
            if qty <= 0:
                continue
            targets.append(
                {"code": code, "weight": weight, "target_qty": qty, "price": price}
            )

        return {"trade_date": trade_date.isoformat(), "targets": targets}

    async def rebalance(self, user_id: int, portfolio_id: int) -> dict:
        """触发再平衡：经风控 + PaperGateway 执行买卖订单。"""
        preview = await self._compute_rebalance_targets(user_id, portfolio_id)
        trading = TradingService(self._session)
        positions = {p.code: p for p in await self._repo.list_positions(portfolio_id)}
        target_codes = {t["code"] for t in preview["targets"]}
        executed: list[dict] = []

        # 先卖后买
        for code, pos in list(positions.items()):
            if code not in target_codes and pos.avail_qty > 0:
                order = await trading.submit_order(
                    user_id,
                    portfolio_id,
                    OrderCreate(code=code, side="sell", qty=pos.avail_qty, order_type="limit", price=float(pos.last_price or 0)),
                )
                executed.append(order)

        for t in preview["targets"]:
            code = t["code"]
            target_qty = int(t["target_qty"])
            cur = positions.get(code)
            cur_qty = cur.qty if cur else 0
            diff = target_qty - cur_qty
            price = float(t["price"])
            if diff < 0 and cur and cur.avail_qty > 0:
                sell_qty = min(-diff, cur.avail_qty)
                sell_qty = int(sell_qty / 100) * 100
                if sell_qty > 0:
                    order = await trading.submit_order(
                        user_id,
                        portfolio_id,
                        OrderCreate(code=code, side="sell", qty=sell_qty, order_type="limit", price=price),
                    )
                    executed.append(order)
            elif diff > 0:
                buy_qty = int(diff / 100) * 100
                if buy_qty > 0:
                    order = await trading.submit_order(
                        user_id,
                        portfolio_id,
                        OrderCreate(code=code, side="buy", qty=buy_qty, order_type="limit", price=price),
                    )
                    executed.append(order)

        result = RebalanceResultView(
            trade_date=preview["trade_date"],
            targets=preview["targets"],
            orders=executed,
            message=f"再平衡完成，共执行 {len(executed)} 笔订单（经风控 + Paper 撮合）",
        )
        return result.model_dump()

    async def _require_owned(self, portfolio_id: int, user_id: int) -> Portfolio:
        p = await self._repo.get_owned(portfolio_id, user_id)
        if p is None:
            raise NotFoundError("组合不存在")
        return p
