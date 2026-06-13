"""内置策略模板库（配置式，M3 首选交付）。"""

from __future__ import annotations

from app.features.strategies.schema import StrategyTemplateView

STRATEGY_TEMPLATES: list[StrategyTemplateView] = [
    StrategyTemplateView(
        id="ma_cross",
        name="双均线交叉",
        description="短期均线上穿长期均线买入，下穿卖出；经典趋势跟踪策略。",
        type="config",
        config={
            "signals": [{"type": "ma_cross", "fast": 5, "slow": 20}],
            "rebalance": {"freq": "week"},
            "position": {"scheme": "equal_weight", "max_n": 10},
            "stop": {"stop_loss": 0.08, "take_profit": 0.2},
        },
        params_schema={
            "fast": {"type": "int", "min": 2, "max": 60, "default": 5},
            "slow": {"type": "int", "min": 5, "max": 250, "default": 20},
        },
        default_params={"fast": 5, "slow": 20},
        universe={"type": "all"},
    ),
    StrategyTemplateView(
        id="momentum_rotation",
        name="动量轮动",
        description="按 N 日动量排名选取强势股，定期再平衡轮动。",
        type="config",
        config={
            "signals": [{"type": "factor_rank", "factor": "momentum_20", "top": 0.1}],
            "rebalance": {"freq": "month"},
            "position": {"scheme": "equal_weight", "max_n": 20},
        },
        params_schema={
            "lookback": {"type": "int", "min": 5, "max": 120, "default": 20},
            "top_pct": {"type": "float", "min": 0.01, "max": 0.5, "default": 0.1},
        },
        default_params={"lookback": 20, "top_pct": 0.1},
        universe={"type": "all"},
    ),
    StrategyTemplateView(
        id="bollinger",
        name="布林带均值回归",
        description="价格触及下轨买入、上轨卖出，适合震荡市。",
        type="config",
        config={
            "signals": [{"type": "bollinger", "period": 20, "std": 2.0}],
            "rebalance": {"freq": "week"},
            "position": {"scheme": "equal_weight", "max_n": 15},
        },
        params_schema={
            "period": {"type": "int", "min": 10, "max": 60, "default": 20},
            "std": {"type": "float", "min": 1.0, "max": 3.0, "default": 2.0},
        },
        default_params={"period": 20, "std": 2.0},
        universe={"type": "all"},
    ),
    StrategyTemplateView(
        id="rsi",
        name="RSI 超买超卖",
        description="RSI 低于超卖线买入、高于超买线卖出。",
        type="config",
        config={
            "signals": [
                {"type": "rsi", "period": 14, "oversold": 30, "overbought": 70}
            ],
            "rebalance": {"freq": "week"},
            "position": {"scheme": "equal_weight", "max_n": 10},
            "stop": {"stop_loss": 0.1},
        },
        params_schema={
            "period": {"type": "int", "min": 5, "max": 30, "default": 14},
            "oversold": {"type": "float", "default": 30},
            "overbought": {"type": "float", "default": 70},
        },
        default_params={"period": 14, "oversold": 30, "overbought": 70},
        universe={"type": "all"},
    ),
    StrategyTemplateView(
        id="factor_stock_pick",
        name="因子选股",
        description="多因子打分排名选股，等权持有 Top N。",
        type="config",
        config={
            "signals": [{"type": "factor_rank", "factor": "composite", "top": 0.05}],
            "rebalance": {"freq": "month"},
            "position": {"scheme": "equal_weight", "max_n": 30},
        },
        params_schema={
            "top_pct": {"type": "float", "min": 0.01, "max": 0.2, "default": 0.05},
            "max_n": {"type": "int", "min": 5, "max": 100, "default": 30},
        },
        default_params={"top_pct": 0.05, "max_n": 30},
        universe={"type": "all"},
    ),
    StrategyTemplateView(
        id="trend_pyramid",
        name="底部启动·均线多头排列·浮盈加仓",
        description=(
            "启动阶段建 20% 观察仓（沿 MA5 稳步推升）；观察期止损更严，"
            "短期多头(MA5>MA10>MA20)未打开或跌破阈值即止损；"
            "多头打开后分两步各加 40%，中期排列(MA20>MA30>MA40)确认后移动止盈。"
        ),
        type="config",
        config={
            "signals": [
                {
                    "type": "ma_trend",
                    "launch": {
                        "bias_ma": 5,
                        "bias_range": [0.0, 0.08],
                        "slope_ma": 5,
                        "slope_window": 5,
                        "above_ma": 5,
                        "above_ratio": 0.8,
                        "above_window": 10,
                    },
                    "tiers": [
                        {"mas": [5, 10, 20], "role": "entry"},
                        {"mas": [20, 30, 40], "role": "add"},
                    ],
                    "slope_ma": 20,
                    "slope_window": 5,
                }
            ],
            "rebalance": {"freq": "day"},
            "position": {
                "scheme": "pyramid",
                "max_n": 10,
                "scale_in": {
                    "init_weight": 0.2,
                    "observe_days": 5,
                    "add_steps": 2,
                    "add_weight": 0.4,
                    "trigger": "short_align",
                    "add_triggers": ["short_align", "medium_align"],
                },
            },
            "stop": {
                "observe_stop_loss": 0.05,
                "stop_loss": 0.08,
                "trailing": 0.12,
            },
        },
        params_schema={
            "bias_upper": {"type": "float", "min": 0.02, "max": 0.2, "default": 0.08},
            "observe_stop_loss": {
                "type": "float",
                "min": 0.02,
                "max": 0.15,
                "default": 0.05,
            },
            "observe_days": {"type": "int", "min": 1, "max": 10, "default": 5},
            "add_steps": {"type": "int", "min": 0, "max": 5, "default": 2},
            "trailing": {"type": "float", "min": 0.05, "max": 0.3, "default": 0.12},
        },
        default_params={
            "bias_upper": 0.08,
            "observe_stop_loss": 0.05,
            "observe_days": 5,
            "add_steps": 2,
            "trailing": 0.12,
        },
        universe={"type": "all"},
    ),
    StrategyTemplateView(
        id="index_ma_cross",
        name="指数成分双均线",
        description="在沪深300成分股内做双均线交叉（指数成分接口待上游支持，暂以全市场降级）。",
        type="config",
        config={
            "signals": [{"type": "ma_cross", "fast": 10, "slow": 30}],
            "rebalance": {"freq": "week"},
            "position": {"scheme": "equal_weight", "max_n": 20},
        },
        params_schema={
            "fast": {"type": "int", "default": 10},
            "slow": {"type": "int", "default": 30},
        },
        default_params={"fast": 10, "slow": 30},
        universe={"type": "index", "code": "000300"},
    ),
]


def list_templates() -> list[StrategyTemplateView]:
    return list(STRATEGY_TEMPLATES)


def get_template(template_id: str) -> StrategyTemplateView | None:
    for tpl in STRATEGY_TEMPLATES:
        if tpl.id == template_id:
            return tpl
    return None
