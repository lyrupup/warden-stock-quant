"""配置式策略编译：从 M3 JSON 提取信号参数与再平衡规则。"""

from __future__ import annotations

from typing import Any


class ConfigStrategyCompiler:
    """解析 M3 配置式策略，供模拟器消费。"""

    def __init__(self, config: dict[str, Any], params: dict[str, Any] | None = None) -> None:
        self._config = config or {}
        self._params = params or {}
        self._signals = self._config.get("signals") or []
        if not self._signals:
            raise ValueError("策略配置缺少 signals")
        self._primary = self._signals[0]
        self._signal_type = self._primary.get("type")
        self._rebalance = (self._config.get("rebalance") or {}).get("freq", "day")
        self._position = self._config.get("position") or {}
        self._stop = self._config.get("stop") or {}

    @property
    def signal_type(self) -> str:
        return str(self._signal_type)

    @property
    def rebalance_freq(self) -> str:
        return str(self._rebalance)

    @property
    def max_n(self) -> int:
        return int(self._position.get("max_n", 10))

    @property
    def scheme(self) -> str:
        return str(self._position.get("scheme", "equal_weight"))

    @property
    def stop_loss(self) -> float | None:
        v = self._stop.get("stop_loss")
        return float(v) if v is not None else None

    @property
    def take_profit(self) -> float | None:
        v = self._stop.get("take_profit")
        return float(v) if v is not None else None

    @property
    def trailing(self) -> float | None:
        v = self._stop.get("trailing")
        return float(v) if v is not None else None

    def ma_cross_periods(self) -> tuple[int, int]:
        fast = int(self._params.get("fast", self._primary.get("fast", 5)))
        slow = int(self._params.get("slow", self._primary.get("slow", 20)))
        if fast >= slow:
            raise ValueError("快线周期须小于慢线周期")
        return fast, slow

    def supported(self) -> bool:
        return self._signal_type in ("ma_cross",)
