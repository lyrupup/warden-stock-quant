"""M3 校验器单测：ma_trend 多头排列趋势 + 金字塔加仓 + 移动止盈。"""

from __future__ import annotations

from app.features.strategies.templates import get_template, list_templates
from app.features.strategies.validator import validate_config

TREND_PYRAMID_CONFIG = {
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
    "stop": {"observe_stop_loss": 0.05, "stop_loss": 0.08, "trailing": 0.12},
}


def test_trend_pyramid_config_valid():
    assert validate_config(TREND_PYRAMID_CONFIG) == []


def test_ma_trend_requires_mas_or_tiers():
    errors = validate_config({"signals": [{"type": "ma_trend"}]})
    assert any("mas 阶梯或 tiers" in e for e in errors)


def test_ma_trend_mas_must_be_ascending():
    errors = validate_config(
        {"signals": [{"type": "ma_trend", "mas": [20, 10, 5]}]}
    )
    assert any("升序" in e for e in errors)


def test_ma_trend_tiers_need_entry_role():
    errors = validate_config(
        {
            "signals": [
                {
                    "type": "ma_trend",
                    "tiers": [{"mas": [20, 30, 40], "role": "add"}],
                }
            ]
        }
    )
    assert any("role=entry" in e for e in errors)


def test_ma_trend_single_mas_ladder_valid():
    errors = validate_config(
        {"signals": [{"type": "ma_trend", "mas": [5, 10, 20, 30, 40]}]}
    )
    assert errors == []


def test_launch_bias_range_order():
    bad = {
        "signals": [
            {
                "type": "ma_trend",
                "mas": [5, 10, 20],
                "launch": {"bias_range": [0.1, 0.02]},
            }
        ]
    }
    errors = validate_config(bad)
    assert any("bias_range 下限不得大于上限" in e for e in errors)


def test_launch_above_ratio_bounds():
    bad = {
        "signals": [
            {
                "type": "ma_trend",
                "mas": [5, 10, 20],
                "launch": {"above_ratio": 1.5},
            }
        ]
    }
    errors = validate_config(bad)
    assert any("above_ratio" in e for e in errors)


def test_scale_in_total_weight_overflow():
    bad = {
        "signals": [{"type": "ma_trend", "mas": [5, 10, 20]}],
        "position": {
            "scheme": "pyramid",
            "scale_in": {"init_weight": 0.6, "add_steps": 3, "add_weight": 0.3},
        },
    }
    errors = validate_config(bad)
    assert any("总仓位超过 100%" in e for e in errors)


def test_scale_in_trigger_invalid():
    bad = {
        "signals": [{"type": "ma_trend", "mas": [5, 10, 20]}],
        "position": {"scheme": "pyramid", "scale_in": {"trigger": "unknown"}},
    }
    errors = validate_config(bad)
    assert any("scale_in.trigger" in e for e in errors)


def test_trailing_stop_bounds():
    bad = {
        "signals": [{"type": "ma_trend", "mas": [5, 10, 20]}],
        "stop": {"trailing": 1.5},
    }
    errors = validate_config(bad)
    assert any("trailing" in e for e in errors)


def test_pyramid_scheme_allowed():
    cfg = {
        "signals": [{"type": "ma_trend", "mas": [5, 10, 20]}],
        "position": {"scheme": "pyramid", "max_n": 10},
    }
    assert validate_config(cfg) == []


def test_trend_pyramid_template_registered_and_valid():
    tpl = get_template("trend_pyramid")
    assert tpl is not None
    assert tpl.type == "config"
    assert validate_config(tpl.config) == []
    assert any(t.id == "trend_pyramid" for t in list_templates())
