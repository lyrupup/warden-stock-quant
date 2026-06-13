"""配置式策略与代码式策略静态校验。"""

from __future__ import annotations

import ast
from typing import Any, Optional

ALLOWED_SIGNAL_TYPES = frozenset(
    {"ma_cross", "ma_trend", "factor_rank", "rsi", "bollinger", "macd"}
)
ALLOWED_REBALANCE_FREQ = frozenset({"day", "week", "month"})
ALLOWED_POSITION_SCHEME = frozenset(
    {"equal_weight", "market_cap", "factor_weight", "risk_parity", "pyramid"}
)
ALLOWED_SCALE_IN_TRIGGER = frozenset(
    {"trend_up", "new_high", "above_ma5", "short_align", "medium_align"}
)
ALLOWED_MA_TIER_ROLES = frozenset({"entry", "add"})
ALLOWED_UNIVERSE_TYPES = frozenset({"all", "index", "list", "factor"})
FORBIDDEN_CODE_IMPORTS = frozenset(
    {
        "os",
        "sys",
        "socket",
        "subprocess",
        "pathlib",
        "shutil",
        "requests",
        "httpx",
        "urllib",
        "pickle",
        "builtins",
    }
)
FORBIDDEN_CODE_CALLS = frozenset({"open", "eval", "exec", "__import__", "compile"})


def validate_universe(universe: Optional[dict[str, Any]]) -> list[str]:
    """校验股票池定义。"""
    if universe is None:
        return []
    errors: list[str] = []
    utype = universe.get("type", "all")
    if utype not in ALLOWED_UNIVERSE_TYPES:
        errors.append(f"universe.type 不支持: {utype}")
        return errors
    if utype == "index" and not universe.get("code"):
        errors.append("universe.type=index 时必须提供 code")
    if utype == "list":
        codes = universe.get("codes")
        if not codes or not isinstance(codes, list):
            errors.append("universe.type=list 时必须提供非空 codes 列表")
    if utype == "factor" and not universe.get("filter"):
        errors.append("universe.type=factor 时必须提供 filter")
    return errors


def _is_pos_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _validate_ma_list(mas: Any, prefix: str) -> list[str]:
    """校验均线周期列表：正整数、升序（短周期在前）。"""
    errors: list[str] = []
    if not isinstance(mas, list) or len(mas) < 2:
        errors.append(f"{prefix} 须为至少 2 个均线周期的数组")
        return errors
    if not all(_is_pos_int(m) for m in mas):
        errors.append(f"{prefix} 均线周期须为正整数")
        return errors
    if mas != sorted(mas) or len(set(mas)) != len(mas):
        errors.append(f"{prefix} 须为严格升序（短周期在前，如 [5,10,20]）")
    return errors


def _validate_launch(launch: dict[str, Any], prefix: str) -> list[str]:
    """校验启动质量块：乖离率带 + MA 斜率 + 站上占比（沿 MA5 稳步推升）。"""
    errors: list[str] = []
    if not isinstance(launch, dict):
        return [f"{prefix} 须为对象"]

    if "bias_ma" in launch and not _is_pos_int(launch["bias_ma"]):
        errors.append(f"{prefix}.bias_ma 须为正整数")

    bias_range = launch.get("bias_range")
    if bias_range is not None:
        if (
            not isinstance(bias_range, list)
            or len(bias_range) != 2
            or not all(isinstance(x, (int, float)) for x in bias_range)
        ):
            errors.append(f"{prefix}.bias_range 须为 [下限, 上限] 两个数值")
        elif float(bias_range[0]) > float(bias_range[1]):
            errors.append(f"{prefix}.bias_range 下限不得大于上限")

    for key in ("slope_ma", "slope_window", "above_ma", "above_window"):
        if key in launch and not _is_pos_int(launch[key]):
            errors.append(f"{prefix}.{key} 须为正整数")

    above_ratio = launch.get("above_ratio")
    if above_ratio is not None and (
        not isinstance(above_ratio, (int, float)) or not (0 < float(above_ratio) <= 1)
    ):
        errors.append(f"{prefix}.above_ratio 须在 (0, 1] 区间")

    return errors


def _validate_ma_trend(sig: dict[str, Any], index: int) -> list[str]:
    """均线多头排列趋势信号：支持单一 mas 阶梯或分层 tiers（entry/add）。"""
    errors: list[str] = []
    prefix = f"signals[{index}]"
    tiers = sig.get("tiers")
    mas = sig.get("mas")

    if tiers is None and mas is None:
        errors.append(f"{prefix} 须提供 mas 阶梯或 tiers 分层之一")
    if mas is not None:
        errors.extend(_validate_ma_list(mas, f"{prefix}.mas"))
    if tiers is not None:
        if not isinstance(tiers, list) or not tiers:
            errors.append(f"{prefix}.tiers 须为非空数组")
        else:
            roles = []
            for ti, tier in enumerate(tiers):
                if not isinstance(tier, dict):
                    errors.append(f"{prefix}.tiers[{ti}] 须为对象")
                    continue
                errors.extend(_validate_ma_list(tier.get("mas"), f"{prefix}.tiers[{ti}].mas"))
                role = tier.get("role", "entry")
                if role not in ALLOWED_MA_TIER_ROLES:
                    errors.append(
                        f"{prefix}.tiers[{ti}].role 不支持: {role}，支持 entry/add"
                    )
                roles.append(role)
            if "entry" not in roles:
                errors.append(f"{prefix}.tiers 至少需包含一个 role=entry 的分层")

    for key in ("slope_ma", "slope_window", "above_ma", "confirm_days"):
        if key in sig and not _is_pos_int(sig[key]):
            errors.append(f"{prefix}.{key} 须为正整数")

    launch = sig.get("launch")
    if launch is not None:
        errors.extend(_validate_launch(launch, f"{prefix}.launch"))

    return errors


def _validate_signal(sig: dict[str, Any], index: int) -> list[str]:
    errors: list[str] = []
    stype = sig.get("type")
    if not stype or stype not in ALLOWED_SIGNAL_TYPES:
        errors.append(
            f"signals[{index}].type 无效，支持: {', '.join(sorted(ALLOWED_SIGNAL_TYPES))}"
        )
        return errors

    if stype == "ma_trend":
        errors.extend(_validate_ma_trend(sig, index))

    elif stype == "ma_cross":
        fast = sig.get("fast")
        slow = sig.get("slow")
        if not isinstance(fast, int) or fast <= 0:
            errors.append(f"signals[{index}].fast 须为正整数")
        if not isinstance(slow, int) or slow <= 0:
            errors.append(f"signals[{index}].slow 须为正整数")
        if isinstance(fast, int) and isinstance(slow, int) and fast >= slow:
            errors.append(f"signals[{index}] 要求 fast < slow")

    elif stype == "factor_rank":
        if not sig.get("factor"):
            errors.append(f"signals[{index}].factor 不能为空")
        top = sig.get("top", 0.1)
        if not isinstance(top, (int, float)) or not (0 < float(top) <= 1):
            errors.append(f"signals[{index}].top 须在 (0, 1] 区间")

    elif stype == "rsi":
        period = sig.get("period", 14)
        if not isinstance(period, int) or period <= 0:
            errors.append(f"signals[{index}].period 须为正整数")

    elif stype == "bollinger":
        period = sig.get("period", 20)
        if not isinstance(period, int) or period <= 0:
            errors.append(f"signals[{index}].period 须为正整数")

    elif stype == "macd":
        for key in ("fast", "slow", "signal"):
            val = sig.get(key)
            if val is not None and (not isinstance(val, int) or val <= 0):
                errors.append(f"signals[{index}].{key} 须为正整数")

    return errors


def validate_config(config: Optional[dict[str, Any]]) -> list[str]:
    """校验配置式策略 JSON。"""
    if config is None:
        return ["config 不能为空"]
    errors: list[str] = []
    signals = config.get("signals")
    if not signals or not isinstance(signals, list):
        errors.append("config.signals 须为非空数组")
    else:
        for i, sig in enumerate(signals):
            if not isinstance(sig, dict):
                errors.append(f"signals[{i}] 须为对象")
                continue
            errors.extend(_validate_signal(sig, i))

    rebalance = config.get("rebalance")
    if rebalance is not None:
        if not isinstance(rebalance, dict):
            errors.append("config.rebalance 须为对象")
        else:
            freq = rebalance.get("freq", "week")
            if freq not in ALLOWED_REBALANCE_FREQ:
                errors.append(
                    f"rebalance.freq 不支持: {freq}，支持 day/week/month"
                )

    position = config.get("position")
    if position is not None:
        if not isinstance(position, dict):
            errors.append("config.position 须为对象")
        else:
            scheme = position.get("scheme", "equal_weight")
            if scheme not in ALLOWED_POSITION_SCHEME:
                errors.append(f"position.scheme 不支持: {scheme}")
            max_n = position.get("max_n")
            if max_n is not None and (not isinstance(max_n, int) or max_n <= 0):
                errors.append("position.max_n 须为正整数")
            scale_in = position.get("scale_in")
            if scale_in is not None:
                errors.extend(_validate_scale_in(scale_in))

    stop = config.get("stop")
    if stop is not None and isinstance(stop, dict):
        for key in ("stop_loss", "take_profit", "trailing", "observe_stop_loss"):
            val = stop.get(key)
            if val is not None and (
                not isinstance(val, (int, float)) or not (0 < float(val) < 1)
            ):
                errors.append(f"stop.{key} 须在 (0, 1) 区间")

    return errors


def _validate_scale_in(scale_in: Any) -> list[str]:
    """校验金字塔加仓配置：建仓比例 + 观察天数 + 加仓档数/比例 + 触发条件。"""
    errors: list[str] = []
    if not isinstance(scale_in, dict):
        return ["position.scale_in 须为对象"]

    init_weight = scale_in.get("init_weight")
    if init_weight is not None and (
        not isinstance(init_weight, (int, float)) or not (0 < float(init_weight) <= 1)
    ):
        errors.append("scale_in.init_weight 须在 (0, 1] 区间")

    add_weight = scale_in.get("add_weight")
    if add_weight is not None and (
        not isinstance(add_weight, (int, float)) or not (0 < float(add_weight) <= 1)
    ):
        errors.append("scale_in.add_weight 须在 (0, 1] 区间")

    for key in ("observe_days", "add_steps"):
        val = scale_in.get(key)
        if val is not None and (
            isinstance(val, bool) or not isinstance(val, int) or val < 0
        ):
            errors.append(f"scale_in.{key} 须为非负整数")

    trigger = scale_in.get("trigger")
    if trigger is not None and trigger not in ALLOWED_SCALE_IN_TRIGGER:
        errors.append(
            "scale_in.trigger 不支持: "
            f"{trigger}，支持 {', '.join(sorted(ALLOWED_SCALE_IN_TRIGGER))}"
        )

    add_triggers = scale_in.get("add_triggers")
    if add_triggers is not None:
        if not isinstance(add_triggers, list) or not add_triggers:
            errors.append("scale_in.add_triggers 须为非空数组")
        else:
            for i, t in enumerate(add_triggers):
                if t not in ALLOWED_SCALE_IN_TRIGGER:
                    errors.append(
                        f"scale_in.add_triggers[{i}] 不支持: {t}，"
                        f"支持 {', '.join(sorted(ALLOWED_SCALE_IN_TRIGGER))}"
                    )
            steps = scale_in.get("add_steps")
            if isinstance(steps, int) and not isinstance(steps, bool) and len(
                add_triggers
            ) != steps:
                errors.append(
                    "scale_in.add_triggers 长度须与 add_steps 一致"
                )

    # 总仓位不得超过 100%：init + add_steps * add_weight。
    iw = float(init_weight) if isinstance(init_weight, (int, float)) else None
    aw = float(add_weight) if isinstance(add_weight, (int, float)) else None
    steps = scale_in.get("add_steps")
    if iw is not None and aw is not None and isinstance(steps, int) and not isinstance(
        steps, bool
    ):
        if iw + aw * steps > 1.0000001:
            errors.append(
                "scale_in 总仓位超过 100%："
                f"init_weight + add_steps×add_weight = {iw + aw * steps:.2f}"
            )

    return errors


class _CodeAstVisitor(ast.NodeVisitor):
    """扫描禁用 import 与危险调用。"""

    def __init__(self) -> None:
        self.errors: list[str] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            root = alias.name.split(".")[0]
            if root in FORBIDDEN_CODE_IMPORTS:
                self.errors.append(f"禁止导入模块: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        mod = (node.module or "").split(".")[0]
        if mod in FORBIDDEN_CODE_IMPORTS:
            self.errors.append(f"禁止导入模块: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CODE_CALLS:
            self.errors.append(f"禁止调用: {node.func.id}()")
        self.generic_visit(node)


def validate_code(code: Optional[str]) -> list[str]:
    """代码式策略 AST 静态检查（沙箱执行留待后续阶段）。"""
    if not code or not code.strip():
        return ["code 不能为空"]
    errors: list[str] = []
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return [f"语法错误: {exc.msg} (line {exc.lineno})"]

    visitor = _CodeAstVisitor()
    visitor.visit(tree)
    errors.extend(visitor.errors)

    # 要求继承 backtrader Strategy（宽松检查类名）
    has_strategy_class = any(
        isinstance(node, ast.ClassDef) for node in tree.body
    )
    if not has_strategy_class:
        errors.append("代码须包含 Strategy 子类定义")

    return errors
