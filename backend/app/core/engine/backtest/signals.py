"""信号计算层：把配置式信号统一编译为「每日持仓状态」。

设计目标：模拟器只关心「某标的在某交易日是否应被持有/选中」，而把各类
技术信号（均线、RSI、MACD、布林带、均线多头排列）的指标计算与状态判定收敛
到本模块，便于扩展与单测。

约定：
- 输入 ``calendar`` 为回测含预热期的交易日（升序）。
- 每个标的输出长度等于 ``calendar`` 的布尔数组：True 表示「该日持有/选中」。
- 缺失数据（停牌/未上市/指标未预热）一律视为 False，不参与持仓。
- 对「entry/exit」型信号（RSI、布林带）使用持仓状态机：进入后保持，
  直到触发退出条件，避免逐日抖动。
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

SUPPORTED_SIGNALS = ("ma_cross", "ma_trend", "rsi", "bollinger", "macd", "factor_rank")


def _closes_series(bars, calendar: list) -> pd.Series:
    """将标的收盘价对齐到 calendar，缺失为 NaN。"""
    date_to_close = {d: bars.close[j] for j, d in enumerate(bars.dates)}
    data = [date_to_close.get(d, np.nan) for d in calendar]
    return pd.Series(data, index=pd.Index(range(len(calendar))), dtype=float)


def _ma(series: pd.Series, window: int) -> pd.Series:
    return series.rolling(window=window, min_periods=window).mean()


def _rsi(series: pd.Series, period: int) -> pd.Series:
    """Wilder RSI（基于 EMA 平滑）。"""
    delta = series.diff()
    gain = delta.clip(lower=0.0)
    loss = (-delta).clip(lower=0.0)
    avg_gain = gain.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1.0 / period, min_periods=period, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    # avg_loss 为 0（持续上涨）时 RSI=100
    rsi = rsi.where(avg_loss != 0.0, 100.0)
    return rsi


def _macd(series: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series]:
    ema_fast = series.ewm(span=fast, min_periods=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, min_periods=slow, adjust=False).mean()
    dif = ema_fast - ema_slow
    dea = dif.ewm(span=signal, min_periods=signal, adjust=False).mean()
    return dif, dea


def _bollinger(
    series: pd.Series, period: int, k: float
) -> tuple[pd.Series, pd.Series, pd.Series]:
    mid = series.rolling(window=period, min_periods=period).mean()
    std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = mid + k * std
    lower = mid - k * std
    return mid, upper, lower


def _state_machine(enter: np.ndarray, exit_: np.ndarray, valid: np.ndarray) -> np.ndarray:
    """持仓状态机：满足 enter 进入并保持，满足 exit 退出。

    enter/exit 为同长布尔数组；valid 标识当日指标是否有效（无效日维持原状态但
    不持仓输出 False）。
    """
    n = len(enter)
    out = np.zeros(n, dtype=bool)
    holding = False
    for i in range(n):
        if not valid[i]:
            out[i] = False
            continue
        if holding:
            if exit_[i]:
                holding = False
        else:
            if enter[i]:
                holding = True
        out[i] = holding
    return out


def _hold_ma_cross(closes: pd.Series, sig: dict, params: dict) -> np.ndarray:
    fast = int(params.get("fast", sig.get("fast", 5)))
    slow = int(params.get("slow", sig.get("slow", 20)))
    if fast >= slow:
        raise ValueError("快线周期须小于慢线周期")
    fast_ma = _ma(closes, fast)
    slow_ma = _ma(closes, slow)
    hold = (fast_ma > slow_ma) & fast_ma.notna() & slow_ma.notna()
    return hold.to_numpy(dtype=bool)


def _hold_ma_trend(closes: pd.Series, sig: dict, params: dict) -> np.ndarray:
    """均线多头排列选股层：短期均线依次向上排列即视为持有。

    默认看 ma5>ma10>ma20；可通过 signal.tiers 或 periods 覆盖。
    完整金字塔加仓由模拟器的 pyramid 路径处理，此处仅给出趋势成立的选股信号。
    """
    periods = params.get("periods") or sig.get("periods")
    if not periods:
        tiers = sig.get("tiers") or {}
        periods = tiers.get("short") or [5, 10, 20]
    periods = [int(p) for p in periods]
    mas = [_ma(closes, p) for p in periods]
    cond = pd.Series(True, index=closes.index)
    for a, b in zip(mas, mas[1:]):
        cond = cond & (a > b) & a.notna() & b.notna()
    return cond.to_numpy(dtype=bool)


def _hold_macd(closes: pd.Series, sig: dict, params: dict) -> np.ndarray:
    fast = int(params.get("fast", sig.get("fast", 12)))
    slow = int(params.get("slow", sig.get("slow", 26)))
    signal = int(params.get("signal", sig.get("signal", 9)))
    dif, dea = _macd(closes, fast, slow, signal)
    hold = (dif > dea) & dif.notna() & dea.notna()
    return hold.to_numpy(dtype=bool)


def _hold_rsi(closes: pd.Series, sig: dict, params: dict) -> np.ndarray:
    period = int(params.get("period", sig.get("period", 14)))
    oversold = float(params.get("oversold", sig.get("oversold", 30)))
    overbought = float(params.get("overbought", sig.get("overbought", 70)))
    rsi = _rsi(closes, period)
    valid = rsi.notna().to_numpy(dtype=bool)
    arr = rsi.to_numpy(dtype=float)
    enter = np.where(valid, arr < oversold, False)
    exit_ = np.where(valid, arr > overbought, False)
    return _state_machine(enter, exit_, valid)


def _hold_bollinger(closes: pd.Series, sig: dict, params: dict) -> np.ndarray:
    period = int(params.get("period", sig.get("period", 20)))
    k = float(params.get("std", sig.get("std", 2.0)))
    mid, _upper, lower = _bollinger(closes, period, k)
    valid = mid.notna().to_numpy(dtype=bool)
    close_arr = closes.to_numpy(dtype=float)
    lower_arr = lower.to_numpy(dtype=float)
    mid_arr = mid.to_numpy(dtype=float)
    # 触下轨买入，回到中轨止盈（均值回归）
    enter = np.where(valid, close_arr < lower_arr, False)
    exit_ = np.where(valid, close_arr > mid_arr, False)
    return _state_machine(enter, exit_, valid)


_DISPATCH = {
    "ma_cross": _hold_ma_cross,
    "ma_trend": _hold_ma_trend,
    "macd": _hold_macd,
    "rsi": _hold_rsi,
    "bollinger": _hold_bollinger,
}


def _alignment(mas: list[pd.Series]) -> pd.Series:
    """多头排列：mas 依次严格递减（短周期 > 长周期）。"""
    cond = pd.Series(True, index=mas[0].index)
    for a, b in zip(mas, mas[1:]):
        cond = cond & (a > b) & a.notna() & b.notna()
    return cond


def _tier_mas(signal: dict, role: str, default: list[int]) -> list[int]:
    for t in signal.get("tiers") or []:
        if t.get("role") == role and t.get("mas"):
            return [int(m) for m in t["mas"]]
    return default


def compute_ma_trend_layers(
    signal: dict[str, Any],
    params: dict[str, Any],
    bars_by_code: dict,
    calendar: list,
) -> dict[str, dict[str, np.ndarray]]:
    """为金字塔加仓计算每标的的分层状态。

    返回每标的：
    - ``entry``：建仓许可 = 短期多头排列(entry tier) ∧ 启动质量(launch)
    - ``add``：加仓确认 = 中期多头排列(add tier，即 medium_align 触发)
    - ``trend``：趋势维持 = 短期多头排列(仅排列，不含启动质量)，用于离场判定
    """
    params = params or {}
    launch = signal.get("launch") or {}
    entry_mas = _tier_mas(signal, "entry", [5, 10, 20])
    add_mas = _tier_mas(signal, "add", [20, 30, 40])

    bias_ma = int(launch.get("bias_ma", entry_mas[0]))
    bias_range = launch.get("bias_range", [0.0, 0.08])
    bias_lo, bias_hi = float(bias_range[0]), float(bias_range[1])
    slope_ma = int(launch.get("slope_ma", entry_mas[0]))
    slope_window = int(launch.get("slope_window", 5))
    above_ma = int(launch.get("above_ma", entry_mas[0]))
    above_ratio = float(launch.get("above_ratio", 0.8))
    above_window = int(launch.get("above_window", 10))

    result: dict[str, dict[str, np.ndarray]] = {}
    for code, bars in bars_by_code.items():
        closes = _closes_series(bars, calendar)
        entry_align = _alignment([_ma(closes, p) for p in entry_mas])
        add_align = _alignment([_ma(closes, p) for p in add_mas])

        # 启动质量：沿 MA「附近」(乖离率带) + 「稳步推升」(斜率>0 且站上占比达标)
        ma_b = _ma(closes, bias_ma)
        bias = (closes - ma_b) / ma_b
        bias_ok = (bias >= bias_lo) & (bias <= bias_hi)
        ma_s = _ma(closes, slope_ma)
        slope_ok = ma_s > ma_s.shift(slope_window)
        ma_a = _ma(closes, above_ma)
        above = (closes >= ma_a).astype(float)
        above_ok = above.rolling(above_window, min_periods=above_window).mean() >= above_ratio
        launch_ok = bias_ok & slope_ok & above_ok

        result[code] = {
            "entry": (entry_align & launch_ok).fillna(False).to_numpy(dtype=bool),
            "add": add_align.fillna(False).to_numpy(dtype=bool),
            "trend": entry_align.fillna(False).to_numpy(dtype=bool),
        }
    return result


def compute_factor_rank_states(
    signal: dict[str, Any],
    matrix: dict[str, np.ndarray],
    calendar: list,
    trade_date,
    top: float,
) -> dict[str, bool]:
    """截面因子排名选股：返回某日被选中的标的。"""
    if trade_date not in calendar:
        return {code: False for code in matrix}
    idx = calendar.index(trade_date)
    scores: list[tuple[str, float]] = []
    for code, arr in matrix.items():
        if idx >= len(arr):
            continue
        v = arr[idx]
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        scores.append((code, float(v)))
    if not scores:
        return {code: False for code in matrix}
    scores.sort(key=lambda x: x[1], reverse=True)
    n_pick = max(1, int(len(scores) * top))
    picked = {c for c, _ in scores[:n_pick]}
    return {code: code in picked for code in matrix}


def select_factor_rank_codes(
    matrix: dict[str, np.ndarray],
    calendar: list,
    day_index: int,
    top: float,
    max_n: int,
) -> list[str]:
    """回测用：按因子值选取 top 比例标的（最多 max_n）。"""
    scores: list[tuple[str, float]] = []
    for code, arr in matrix.items():
        if day_index >= len(arr):
            continue
        v = arr[day_index]
        if v is None or (isinstance(v, float) and np.isnan(v)):
            continue
        scores.append((code, float(v)))
    if not scores:
        return []
    scores.sort(key=lambda x: x[1], reverse=True)
    n_pick = max(1, int(len(scores) * top))
    return [c for c, _ in scores[: min(n_pick, max_n)]]


def is_supported(signal_type: str) -> bool:
    return signal_type in SUPPORTED_SIGNALS


def compute_hold_states(
    signal: dict[str, Any],
    params: dict[str, Any],
    bars_by_code: dict,
    calendar: list,
) -> dict[str, np.ndarray]:
    """计算每个标的在 calendar 上的持仓布尔状态。"""
    signal_type = signal.get("type")
    fn = _DISPATCH.get(str(signal_type))
    if fn is None:
        raise ValueError(f"暂不支持的信号类型: {signal_type}")
    states: dict[str, np.ndarray] = {}
    for code, bars in bars_by_code.items():
        closes = _closes_series(bars, calendar)
        states[code] = fn(closes, signal, params or {})
    return states
