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


def run_backtest(
    inp: BacktestEngineInput,
    on_progress: Optional[ProgressCallback] = None,
    should_cancel: Optional[CancelCallback] = None,
) -> BacktestEngineOutput:
    """执行日频回测（首期支持 ma_cross + equal_weight）。"""
    compiler = ConfigStrategyCompiler(inp.strategy_config, inp.params)
    if not compiler.supported():
        raise ValueError(f"暂不支持的信号类型: {compiler.signal_type}")

    calendar = _filter_calendar(inp.calendar, inp.date_from, inp.date_to)
    if len(calendar) < 2:
        raise ValueError("回测区间交易日不足")

    fast, slow = compiler.ma_cross_periods()
    states = _compute_ma_states(inp.bars_by_code, calendar, fast, slow)

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

        # 盘中止损止盈（以收盘价检查）
        _apply_stops(dt, portfolio, inp, compiler, trades, calendar, i)

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


def _compute_ma_states(
    bars_by_code: dict[str, BarData],
    calendar: list[date],
    fast: int,
    slow: int,
) -> dict[str, np.ndarray]:
    """每个标的在 calendar 上 fast>slow 的布尔状态。"""
    states: dict[str, np.ndarray] = {}
    for code, bars in bars_by_code.items():
        arr = np.zeros(len(calendar), dtype=bool)
        date_to_close = {d: bars.close[j] for j, d in enumerate(bars.dates)}
        closes = np.array([date_to_close.get(d, np.nan) for d in calendar], dtype=float)
        valid = np.isfinite(closes)
        if np.sum(valid) < slow:
            states[code] = arr
            continue
        fast_ma = _rolling_mean_on_calendar(closes, fast)
        slow_ma = _rolling_mean_on_calendar(closes, slow)
        bullish = (fast_ma > slow_ma) & np.isfinite(fast_ma) & np.isfinite(slow_ma)
        arr = bullish
        states[code] = arr
    return states


def _rolling_mean_on_calendar(values: np.ndarray, window: int) -> np.ndarray:
    out = np.full(len(values), np.nan)
    for i in range(len(values)):
        if i + 1 < window:
            continue
        chunk = values[i - window + 1 : i + 1]
        if np.all(np.isfinite(chunk)):
            out[i] = np.mean(chunk)
    return out


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
) -> None:
    prices = _close_prices(inp.bars_by_code, dt)
    stop_loss = compiler.stop_loss
    take_profit = compiler.take_profit
    trailing = compiler.trailing
    for code, h in list(portfolio.holdings.items()):
        if h.qty <= 0 or h.avail_qty <= 0:
            continue
        price = prices.get(code)
        if not price or not _can_sell(inp.bars_by_code.get(code), dt, price):
            continue
        h.high_price = max(h.high_price, price)
        ret = (price - h.cost_price) / h.cost_price if h.cost_price > 0 else 0.0
        drawdown_from_high = (price - h.high_price) / h.high_price if h.high_price > 0 else 0.0
        should_sell = False
        if stop_loss is not None and ret <= -stop_loss:
            should_sell = True
        if take_profit is not None and ret >= take_profit:
            should_sell = True
        if trailing is not None and drawdown_from_high <= -trailing:
            should_sell = True
        if should_sell:
            _sell(dt, code, h.avail_qty, price, h, portfolio, inp.cost, trades)
