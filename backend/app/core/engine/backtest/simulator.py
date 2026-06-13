"""日频组合模拟器（pandas/numpy，M4 首期实现）。"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Optional

import numpy as np

from app.core.engine.backtest.compiler import ConfigStrategyCompiler
from app.core.engine.backtest.cost import (
    apply_slippage,
    calc_commission,
    calc_sell_tax,
    round_lot,
)
from app.core.engine.backtest.metrics import compute_metrics
from app.core.engine.backtest.signals import (
    compute_hold_states,
    compute_ma_trend_layers,
    select_factor_rank_codes,
)
from app.core.engine.backtest.types import (
    BacktestEngineInput,
    BacktestEngineOutput,
    BarData,
    CancelCallback,
    EquityPoint,
    PositionSnapshot,
    ProgressCallback,
    TradeRecord,
)


@dataclass
class _Holding:
    qty: int = 0
    avail_qty: int = 0
    cost_price: float = 0.0
    high_price: float = 0.0


@dataclass
class _Portfolio:
    cash: float
    holdings: dict[str, _Holding] = field(default_factory=dict)


@dataclass
class _PyramidState:
    """单标的金字塔加仓状态机。"""

    active: bool = False
    entry_index: int = -1
    added: int = 0  # 已加仓档数


def run_backtest(
    inp: BacktestEngineInput,
    on_progress: Optional[ProgressCallback] = None,
    should_cancel: Optional[CancelCallback] = None,
) -> BacktestEngineOutput:
    """执行日频回测（支持 ma_cross/ma_trend/rsi/bollinger/macd + equal_weight）。"""
    compiler = ConfigStrategyCompiler(inp.strategy_config, inp.params)
    if not compiler.supported():
        raise ValueError(f"暂不支持的信号类型: {compiler.signal_type}")

    # 信号需在含预热期的完整日历上计算指标，再裁剪到回测区间执行
    full_calendar = sorted(inp.calendar)
    calendar = _filter_calendar(full_calendar, inp.date_from, inp.date_to)
    if len(calendar) < 2:
        raise ValueError("回测区间交易日不足")
    cal_index = {d: j for j, d in enumerate(full_calendar)}

    def _align(arr: np.ndarray) -> np.ndarray:
        return np.array([arr[cal_index[d]] for d in calendar], dtype=bool)

    use_pyramid = compiler.is_pyramid and compiler.signal_type == "ma_trend"
    use_factor_rank = compiler.signal_type == "factor_rank"
    if use_factor_rank and not inp.factor_matrix:
        raise ValueError("factor_rank 信号缺少因子数据")
    pyramid_states: dict[str, _PyramidState] = {}
    entry_states: dict[str, np.ndarray] = {}
    add_states: dict[str, np.ndarray] = {}
    trend_states: dict[str, np.ndarray] = {}
    scale_in: dict = {}
    states: dict[str, np.ndarray] = {}

    if use_pyramid:
        scale_in = compiler.scale_in()
        layers = compute_ma_trend_layers(
            compiler.primary_signal, compiler.params, inp.bars_by_code, full_calendar
        )
        for code, lyr in layers.items():
            entry_states[code] = _align(lyr["entry"])
            add_states[code] = _align(lyr["add"])
            trend_states[code] = _align(lyr["trend"])
            pyramid_states[code] = _PyramidState()
    elif not use_factor_rank:
        states_full = compute_hold_states(
            compiler.primary_signal, compiler.params, inp.bars_by_code, full_calendar
        )
        states = {code: _align(st) for code, st in states_full.items()}

    portfolio = _Portfolio(cash=inp.init_capital)
    trades: list[TradeRecord] = []
    positions: list[PositionSnapshot] = []
    equity: list[EquityPoint] = []
    pending_targets: dict[str, float] = {}
    peak_nav = inp.init_capital

    for i, dt in enumerate(calendar):
        if should_cancel and should_cancel():
            raise BacktestCanceledError("回测已取消")

        # T+1：上一交易日买入的份额今日可卖
        if i > 0:
            for h in portfolio.holdings.values():
                h.avail_qty = h.qty

        # 次日开盘撮合：执行上一日收盘产生的目标仓位
        if pending_targets:
            _execute_targets(
                dt,
                pending_targets,
                portfolio,
                inp,
                trades,
                open_prices=_open_prices(inp.bars_by_code, dt),
            )
            pending_targets = {}

        # 盘中止损止盈（以收盘价检查；金字塔观察期用更严止损、确认后启用移动止盈）
        _apply_stops(
            dt, portfolio, inp, compiler, trades, calendar, i,
            pyramid_states=pyramid_states if use_pyramid else None,
        )

        # 日终估值
        close_px = _close_prices(inp.bars_by_code, dt)
        mv = _market_value(portfolio, close_px)
        nav = portfolio.cash + mv
        peak_nav = max(peak_nav, nav)
        dd = (nav - peak_nav) / peak_nav if peak_nav > 0 else 0.0
        bench_nav = _benchmark_nav(inp, dt, calendar[0], nav)
        equity.append(
            EquityPoint(
                trade_date=dt,
                nav=nav,
                benchmark_nav=bench_nav,
                drawdown=dd,
                cash=portfolio.cash,
                market_value=mv,
            )
        )
        positions.extend(_snapshot_positions(dt, portfolio, close_px, nav))

        # 收盘信号 → 下一交易日开盘执行
        if _is_rebalance_day(dt, calendar, i, compiler.rebalance_freq) and i < len(calendar) - 1:
            if use_pyramid:
                pending_targets = _pyramid_targets(
                    i, entry_states, add_states, trend_states,
                    pyramid_states, portfolio, scale_in, compiler.max_n,
                )
            elif use_factor_rank:
                full_idx = cal_index[dt]
                picks = select_factor_rank_codes(
                    inp.factor_matrix or {},
                    full_calendar,
                    full_idx,
                    inp.factor_top,
                    compiler.max_n,
                )
                pending_targets = _weights_from_picks(picks, portfolio)
            else:
                pending_targets = _target_weights(
                    dt, states, compiler.max_n, portfolio, calendar, i
                )

        if on_progress:
            on_progress(round(100.0 * (i + 1) / len(calendar), 2))

    metrics = compute_metrics(equity, trades, inp.init_capital)
    return BacktestEngineOutput(
        equity=equity, trades=trades, positions=positions, metrics=metrics
    )


class BacktestCanceledError(Exception):
    """回测被用户取消。"""


def _filter_calendar(calendar: list[date], start: date, end: date) -> list[date]:
    return [d for d in calendar if start <= d <= end]


def _is_rebalance_day(dt: date, calendar: list[date], i: int, freq: str) -> bool:
    if freq == "day":
        return True
    if freq == "week":
        if i == 0:
            return True
        return dt.isocalendar()[1] != calendar[i - 1].isocalendar()[1]
    if freq == "month":
        if i == 0:
            return True
        return dt.month != calendar[i - 1].month
    return True


def _weights_from_picks(picks: list[str], portfolio: _Portfolio) -> dict[str, float]:
    targets = {code: 0.0 for code in portfolio.holdings}
    if not picks:
        return targets
    w = 1.0 / len(picks)
    for code in picks:
        targets[code] = w
    for code in picks:
        if code not in targets:
            targets[code] = w
    return targets


def _target_weights(
    dt: date,
    states: dict[str, np.ndarray],
    max_n: int,
    portfolio: _Portfolio,
    calendar: list[date],
    i: int,
) -> dict[str, float]:
    idx = i  # calendar index
    selected = [code for code, st in states.items() if idx < len(st) and st[idx]]
    selected.sort()
    if not selected:
        # 清仓
        return {code: 0.0 for code in portfolio.holdings if portfolio.holdings[code].qty > 0}
    picks = selected[:max_n]
    w = 1.0 / len(picks)
    targets = {code: 0.0 for code in portfolio.holdings}
    for code in picks:
        targets[code] = w
    return targets


def _pyramid_targets(
    i: int,
    entry_states: dict[str, np.ndarray],
    add_states: dict[str, np.ndarray],
    trend_states: dict[str, np.ndarray],
    pstates: dict[str, _PyramidState],
    portfolio: _Portfolio,
    scale_in: dict,
    max_n: int,
) -> dict[str, float]:
    """金字塔目标权重：建仓→观察→分批加仓→趋势破位离场。

    单标的目标权重 = min(init_weight + 已加档数 × add_weight, 1.0)；同时持仓数受
    max_n 约束；现金不足由撮合层自然限制。
    """
    init_w = scale_in["init_weight"]
    add_w = scale_in["add_weight"]
    add_steps = scale_in["add_steps"]
    observe_days = scale_in["observe_days"]
    targets: dict[str, float] = {}
    active_count = sum(1 for s in pstates.values() if s.active)

    for code in sorted(pstates.keys()):
        s = pstates[code]
        entry = bool(entry_states[code][i]) if i < len(entry_states[code]) else False
        add = bool(add_states[code][i]) if i < len(add_states[code]) else False
        trend = bool(trend_states[code][i]) if i < len(trend_states[code]) else False

        if s.active:
            if not trend:
                # 趋势排列破位 → 清仓离场
                s.active = False
                s.entry_index = -1
                s.added = 0
                targets[code] = 0.0
                active_count -= 1
                continue
            # 满足触发且过观察期 → 加仓一档
            if s.added < add_steps and add and (i - s.entry_index) >= observe_days:
                s.added += 1
            targets[code] = min(init_w + s.added * add_w, 1.0)
        else:
            if entry and active_count < max_n:
                s.active = True
                s.entry_index = i
                s.added = 0
                active_count += 1
                targets[code] = init_w
    return targets


def _open_prices(bars_by_code: dict[str, BarData], dt: date) -> dict[str, float]:
    out: dict[str, float] = {}
    for code, bars in bars_by_code.items():
        if dt in bars.dates:
            j = bars.dates.index(dt)
            if not bars.suspended[j] and bars.open[j]:
                out[code] = float(bars.open[j])
    return out


def _close_prices(bars_by_code: dict[str, BarData], dt: date) -> dict[str, float]:
    out: dict[str, float] = {}
    for code, bars in bars_by_code.items():
        if dt in bars.dates:
            j = bars.dates.index(dt)
            if bars.close[j]:
                out[code] = float(bars.close[j])
    return out


def _market_value(portfolio: _Portfolio, prices: dict[str, float]) -> float:
    total = 0.0
    for code, h in portfolio.holdings.items():
        if h.qty > 0 and code in prices:
            total += h.qty * prices[code]
    return total


def _snapshot_positions(
    dt: date, portfolio: _Portfolio, prices: dict[str, float], nav: float
) -> list[PositionSnapshot]:
    snaps: list[PositionSnapshot] = []
    for code, h in portfolio.holdings.items():
        if h.qty <= 0 or code not in prices:
            continue
        mv = h.qty * prices[code]
        snaps.append(
            PositionSnapshot(
                trade_date=dt,
                code=code,
                qty=h.qty,
                price=prices[code],
                market_value=mv,
                weight=mv / nav if nav > 0 else 0.0,
            )
        )
    return snaps


def _benchmark_nav(
    inp: BacktestEngineInput, dt: date, start: date, _nav: float
) -> Optional[float]:
    if not inp.benchmark_bars or dt not in inp.benchmark_bars.dates:
        return None
    j = inp.benchmark_bars.dates.index(dt)
    j0 = inp.benchmark_bars.dates.index(start) if start in inp.benchmark_bars.dates else 0
    c0 = inp.benchmark_bars.close[j0]
    c1 = inp.benchmark_bars.close[j]
    if not c0 or not c1:
        return None
    return inp.init_capital * float(c1) / float(c0)


def _execute_targets(
    dt: date,
    targets: dict[str, float],
    portfolio: _Portfolio,
    inp: BacktestEngineInput,
    trades: list[TradeRecord],
    open_prices: dict[str, float],
) -> None:
    prices = open_prices
    nav = portfolio.cash + _market_value(portfolio, prices)
    if nav <= 0:
        return

    # 先卖后买
    for code, target_w in targets.items():
        price = prices.get(code)
        if not price or price <= 0:
            continue
        h = portfolio.holdings.setdefault(code, _Holding())
        target_value = nav * target_w
        current_value = h.qty * price
        if target_value < current_value - 1e-6:
            sell_value = current_value - target_value
            sell_qty = round_lot(int(sell_value / price))
            sell_qty = min(sell_qty, h.avail_qty)
            if sell_qty > 0:
                _sell(dt, code, sell_qty, price, h, portfolio, inp.cost, trades)

    nav = portfolio.cash + _market_value(portfolio, prices)
    for code, target_w in targets.items():
        price = prices.get(code)
        if not price or price <= 0:
            continue
        if not _can_buy(inp.bars_by_code.get(code), dt, price):
            continue
        h = portfolio.holdings.setdefault(code, _Holding())
        target_value = nav * target_w
        current_value = h.qty * price
        if target_value > current_value + 1e-6:
            buy_value = target_value - current_value
            buy_qty = round_lot(int(buy_value / price))
            if buy_qty > 0:
                _buy(dt, code, buy_qty, price, h, portfolio, inp.cost, trades)


def _can_buy(bars: Optional[BarData], dt: date, price: float) -> bool:
    if bars is None or dt not in bars.dates:
        return False
    j = bars.dates.index(dt)
    if bars.suspended[j]:
        return False
    limit_up = bars.limit_up[j]
    if limit_up is not None and price >= float(limit_up) * 0.999:
        return False
    return True


def _can_sell(bars: Optional[BarData], dt: date, price: float) -> bool:
    if bars is None or dt not in bars.dates:
        return False
    j = bars.dates.index(dt)
    if bars.suspended[j]:
        return False
    limit_down = bars.limit_down[j]
    if limit_down is not None and price <= float(limit_down) * 1.001:
        return False
    return True


def _buy(
    dt: date,
    code: str,
    qty: int,
    price: float,
    h: _Holding,
    portfolio: _Portfolio,
    cost,
    trades: list[TradeRecord],
) -> None:
    fill = apply_slippage(price, "buy", cost)
    amount = fill * qty
    commission = calc_commission(amount, cost)
    total = amount + commission
    if total > portfolio.cash:
        qty = round_lot(int((portfolio.cash - cost.commission_min) / fill))
        if qty <= 0:
            return
        amount = fill * qty
        commission = calc_commission(amount, cost)
        total = amount + commission
    portfolio.cash -= total
    new_qty = h.qty + qty
    h.cost_price = (h.cost_price * h.qty + fill * qty) / new_qty if new_qty else 0.0
    h.qty = new_qty
    h.high_price = max(h.high_price, fill)
    trades.append(
        TradeRecord(
            trade_date=dt,
            code=code,
            side="buy",
            price=fill,
            qty=qty,
            amount=amount,
            commission=commission,
            tax=0.0,
        )
    )


def _sell(
    dt: date,
    code: str,
    qty: int,
    price: float,
    h: _Holding,
    portfolio: _Portfolio,
    cost,
    trades: list[TradeRecord],
) -> None:
    fill = apply_slippage(price, "sell", cost)
    amount = fill * qty
    commission = calc_commission(amount, cost)
    tax = calc_sell_tax(amount, cost)
    pnl = (fill - h.cost_price) * qty - commission - tax
    portfolio.cash += amount - commission - tax
    h.qty -= qty
    h.avail_qty = max(0, h.avail_qty - qty)
    if h.qty == 0:
        h.cost_price = 0.0
        h.high_price = 0.0
    trades.append(
        TradeRecord(
            trade_date=dt,
            code=code,
            side="sell",
            price=fill,
            qty=qty,
            amount=amount,
            commission=commission,
            tax=tax,
            pnl=pnl,
        )
    )


def _apply_stops(
    dt: date,
    portfolio: _Portfolio,
    inp: BacktestEngineInput,
    compiler: ConfigStrategyCompiler,
    trades: list[TradeRecord],
    calendar: list[date],
    i: int,
    pyramid_states: Optional[dict[str, "_PyramidState"]] = None,
) -> None:
    prices = _close_prices(inp.bars_by_code, dt)
    stop_loss = compiler.stop_loss
    take_profit = compiler.take_profit
    trailing = compiler.trailing
    observe_stop_loss = compiler.observe_stop_loss
    for code, h in list(portfolio.holdings.items()):
        if h.qty <= 0 or h.avail_qty <= 0:
            continue
        price = prices.get(code)
        if not price or not _can_sell(inp.bars_by_code.get(code), dt, price):
            continue
        h.high_price = max(h.high_price, price)
        ret = (price - h.cost_price) / h.cost_price if h.cost_price > 0 else 0.0
        drawdown_from_high = (price - h.high_price) / h.high_price if h.high_price > 0 else 0.0

        # 金字塔：观察期（未加仓）用更严止损；确认加仓后才启用移动止盈
        eff_stop_loss = stop_loss
        eff_trailing = trailing
        if pyramid_states is not None:
            ps = pyramid_states.get(code)
            in_observe = ps is None or ps.added == 0
            if in_observe:
                if observe_stop_loss is not None:
                    eff_stop_loss = observe_stop_loss
                eff_trailing = None  # 观察期不启用移动止盈

        should_sell = False
        if eff_stop_loss is not None and ret <= -eff_stop_loss:
            should_sell = True
        if take_profit is not None and ret >= take_profit:
            should_sell = True
        if eff_trailing is not None and drawdown_from_high <= -eff_trailing:
            should_sell = True
        if should_sell:
            _sell(dt, code, h.avail_qty, price, h, portfolio, inp.cost, trades)
            if pyramid_states is not None and code in pyramid_states:
                # 止损离场后重置金字塔状态，允许后续再次建仓
                pyramid_states[code] = _PyramidState()
