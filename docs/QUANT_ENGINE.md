# 守望者量化交易系统 · 量化引擎设计文档

> Warden Stock Quant · Quant Engine Design（回测 / 因子 / 执行 / 风控 / 绩效）
>
> 前置阅读：[`PRD.md`](./PRD.md) · [`BACKEND.md`](./BACKEND.md) · [`DATA_ACCESS.md`](./DATA_ACCESS.md)
>
> 本文档定义 `app/core/engine/*` 与 `app/core/data/feed/*` 的内部设计，是 M4/M5/M6/M8/M9 的技术底座。所有引擎**不依赖 FastAPI**，可在 worker、CLI、测试中独立运行。

---

## 1. 设计原则

1. **抽象优先、可插拔**：回测引擎、执行网关、因子计算、风控规则、数据源均面向接口编程，便于替换实现（如 backtrader → vectorbt）。
2. **PIT 无未来函数**：所有取数经 DataFeed，按 `as_of_date` 截断；指标用 data 服务 PIT 快照或本地一致重算。
3. **回测/仿真/实盘口径一致**：A 股交易规则、成本模型、风控引擎三者在回测与实盘中复用同一套实现，降低「回测好看、实盘走样」。
4. **确定性可复现**：固定随机种子、固定数据版本、固定参数 → 同样输入必得同样输出。
5. **任务化与可中断**：长任务在 Celery worker 运行，周期检查取消标志，进度可上报。

---

## 2. 框架选型与封装策略

### 2.1 调研结论（2026）

| 框架 | 定位 | 现状 | 本项目用途 |
|------|------|------|-----------|
| **backtrader** | 事件驱动回测 + 实盘 | 功能强、API 友好、自带指标/analyzer，但官方 2019 后近乎停更（社区 fork backtrader2），Python 3.10+ 需留意兼容 | **主回测引擎**（封装在抽象层后）|
| **vnpy** | 实盘/仿真交易框架 | 活跃；A 股经 XTP/tora/OST/EMT 网关，但实盘有强合规门槛 | **执行内核 + 网关**（仿真默认、实盘自托管）|
| vectorbt | 向量化回测 | 极快、适合大规模参数寻优，无原生实盘 | 可选：参数寻优加速 |
| zipline-reloaded | 研究 + Pipeline | 社区维护，适合因子研究 | 可选：因子 Pipeline 研究 |
| alphalens-reloaded | 因子分析 | 社区维护 | 因子 IC/分层分析参考实现 |
| quantstats / empyrical-reloaded | 绩效分析 | 维护中 | 绩效指标与报告 |

**策略**：用 backtrader 作为主回测引擎（用户指定、生态成熟），但**以 `IBacktestEngine` 抽象封装**，避免锁死；参数寻优场景可切 vectorbt；因子研究自实现 alphalens 风格指标（依赖少、口径可控）。明确记录 backtrader 维护风险，锁定可用版本（建议 `backtrader2` 或 pin 兼容版本 + 自带补丁）。

### 2.2 引擎抽象接口

```python
# app/core/engine/backtest/base.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class BacktestSpec:
    strategy: "StrategyDef"        # 配置式或代码式
    params: dict
    universe: "Universe"
    date_from: str; date_to: str
    init_capital: float
    adjust: str = "qfq"
    cost: "CostModel" = None
    benchmark: str = "000300"

@dataclass
class BacktestResult:
    equity: "pd.DataFrame"         # date, nav, benchmark_nav, drawdown, cash, mv
    trades: "pd.DataFrame"         # date, code, side, price, qty, amount, commission, tax, pnl
    positions: "pd.DataFrame"      # date, code, qty, price, mv, weight
    metrics: dict
    logs: list[str]

class IBacktestEngine(Protocol):
    def run(self, spec: BacktestSpec, feed: "DataFeed",
            on_progress=None, should_cancel=None) -> BacktestResult: ...
```

实现：`BacktraderEngine(IBacktestEngine)`、（可选）`VectorbtEngine`。

---

## 3. 数据访问层（DataFeed）

DataFeed 是引擎与数据集之间的唯一取数入口，保证 PIT 与口径一致（数据集落地见 `DATA_ACCESS.md`）。

```python
# app/core/data/feed/base.py
class DataFeed(Protocol):
    def trading_calendar(self, start, end) -> list[date]: ...
    def get_universe(self, as_of: date, scheme: "Universe") -> list[str]: ...
    def get_bars(self, codes, start, end, period="day", adjust="qfq") -> "pd.DataFrame": ...
    def get_indicators(self, codes, as_of: date, types: list[str]) -> "pd.DataFrame": ...   # PIT 快照
    def get_limit_status(self, code, d: date) -> "LimitStatus": ...   # 涨跌停/停牌/ST
    def is_tradable(self, code, d: date) -> bool: ...
    def get_index(self, code, start, end) -> "pd.DataFrame": ...      # 基准
```

- **回测 DataFeed**：从本地数据集（PostgreSQL / Parquet）批量读，构造 backtrader `PandasData` feed，预加载区间内全部 bar，按事件回放。
- **实盘/仿真 DataFeed**：盘后取最新收盘数据（经平台 data 客户端），供调仓决策。
- **缓存**：区间 bar 与因子值用 Redis/本地内存缓存，避免重复读。

### 3.1 backtrader 数据装载（含 A 股状态位）

为支持涨跌停/停牌/ST 规则，自定义 `PandasData` 增加附加 line：

```python
import backtrader as bt

class AStockData(bt.feeds.PandasData):
    lines = ("limit_up", "limit_down", "suspended", "is_st", "adj_factor")
    params = (
        ("limit_up", -1), ("limit_down", -1), ("suspended", -1),
        ("is_st", -1), ("adj_factor", -1),
    )
```

---

## 4. 回测引擎（M4）

### 4.1 A 股交易规则建模

| 规则 | 实现 |
|------|------|
| **T+1** | 自定义 sizer/broker 逻辑：买入持仓当日 `avail=0`，次日起可卖；卖出仅允许 `avail_qty`。|
| **涨跌停** | 自定义 `Broker`/`fill` 钩子：bar 标记涨停则买单不成交（或排队失败），跌停则卖单不成交；可配「触板撤单」。|
| **停牌/退市/未上市** | DataFeed `is_tradable=false` 的 bar 跳过交易；持仓停牌按最后价估值。|
| **最小交易单位** | Sizer 买入按 100 股向下取整（科创板/创业板特殊单位可配）。|
| **复权** | 默认前复权 `qfq`；价格/指标口径统一，成交按复权价、报告可换算。|
| **撮合时点** | 可配：信号产生于 bar close，撮合于 **next bar open**（默认，避免未来函数）或 close/vwap。|

### 4.2 成本模型

```python
@dataclass
class CostModel:
    commission_rate: float = 0.0003      # 佣金双边
    commission_min: float = 5.0          # 最低 5 元
    stamp_tax_rate: float = 0.0005        # 印花税（卖出单边）
    transfer_fee_rate: float = 0.00001    # 过户费
    slippage_type: str = "pct"            # none|pct|tick|volume
    slippage_value: float = 0.0005
```

接入 backtrader `CommInfo` + 自定义滑点；卖出加印花税，买卖加佣金（取 max(rate, min)）。

### 4.3 执行流程（worker 内）

```
run_backtest(backtest_id):
  1. 载入 strategy_version + params + universe + range
  2. 构建回测 DataFeed（PIT，预读区间 bar + 状态位 + 指标）
  3. 实例化 IBacktestEngine（默认 BacktraderEngine）
  4. 注入策略：
        - config 式 → 由 ConfigStrategyCompiler 编译成 bt.Strategy
        - code 式  → 沙箱加载用户 bt.Strategy 子类
  5. 注入风控（RiskEngine 作为 broker 前置校验）
  6. cerebro.run()：事件回放，on_progress 上报（按交易日比例），should_cancel 检查
  7. 收集 analyzer 输出 → equity/trades/positions
  8. 计算 metrics（§7）→ 写库（流式分批）
  9. 更新 backtests 状态/进度；触发完成告警
```

### 4.4 配置式策略编译器

把 M3 配置式策略（JSON）编译为 backtrader Strategy，内置信号积木：

```jsonc
{
  "universe": { "type": "index", "code": "000300" },  // 默认股票池（仅预填建议，见下方说明）
  "signals": [
    { "type": "ma_cross", "fast": 5, "slow": 20 },          // 金叉买/死叉卖
    { "type": "factor_rank", "factor": "momentum_20", "top": 0.1 } // 因子选股
  ],
  "rebalance": { "freq": "week" },
  "position": { "scheme": "equal_weight", "max_n": 20 },
  "stop": { "stop_loss": 0.08, "take_profit": 0.2 }
}
```

> **股票池语义（重要）**：策略配置中的 `universe` 仅作为「默认股票池」，是新建回测时表单的预填建议，**不属于策略逻辑本身**。任何一次回测/组合真正生效的股票池以其自身记录（`backtests.universe`）为准——创建回测时可覆盖策略默认值，引擎执行与「回测策略快照」展示均以该回测记录的 `universe` 为权威来源。这样同一份策略逻辑可在不同股票池上分别回测对比，无需复制策略版本。

内置信号积木（`signals[].type`）：

| 类型 | 含义 | 关键参数 |
|------|------|----------|
| `ma_cross` | 双均线金叉/死叉 | `fast` < `slow` |
| `ma_trend` | 均线多头排列趋势（分层启动→建仓→加仓） | `launch` / `tiers` / `slope_ma` |
| `factor_rank` | 因子排名选股 | `factor`、`top∈(0,1]` |
| `rsi` | RSI 超买超卖 | `period` |
| `bollinger` | 布林带均值回归 | `period`、`std` |
| `macd` | MACD 金叉/死叉 | `fast`/`slow`/`signal` |

仓位 `position.scheme`：`equal_weight`/`market_cap`/`factor_weight`/`risk_parity`/`pyramid`（金字塔加仓）。
止损止盈 `stop`：`stop_loss`/`take_profit`/`trailing`（移动止盈），均为 (0,1) 小数。

`ConfigStrategyCompiler` 将其转为 `next()` 逻辑：到再平衡日 → 计算信号 → 目标持仓 → 下单（过风控）。这保证非程序员用户也能安全建策略。

### 4.4.1 ma_trend 多头排列趋势 + 金字塔加仓（趋势跟踪范式）

针对「底部启动 → 均线逐级多头排列 → 主升浪」的右侧趋势打法，`ma_trend` 用**启动质量过滤（launch）+ 分层排列确认（tiers）**两段刻画，配合 `position.scale_in` 实现浮盈金字塔加仓：

```jsonc
{
  "signals": [
    {
      "type": "ma_trend",
      // 启动质量：沿 MA5「附近」(乖离率带) +「稳步推升」(斜率/站上占比)
      "launch": {
        "bias_ma": 5,
        "bias_range": [0.0, 0.08],   // BIAS5∈[0,8%]：站上 MA5 但不过度乖离（不追高）
        "slope_ma": 5, "slope_window": 5,   // MA5 斜率>0：在推升
        "above_ma": 5, "above_ratio": 0.8, "above_window": 10  // 近10日≥80%收在MA5上：稳
      },
      // 分层排列：短期打开=建仓许可，中期打开=加仓确认
      "tiers": [
        { "mas": [5, 10, 20], "role": "entry" },   // MA5>MA10>MA20 短期多头 → 建仓
        { "mas": [20, 30, 40], "role": "add" }     // MA20>MA30>MA40 中期多头 → 加仓
      ],
      "slope_ma": 20, "slope_window": 5
    }
  ],
  "rebalance": { "freq": "day" },
  "position": {
    "scheme": "pyramid", "max_n": 10,
    "scale_in": {
      "init_weight": 0.4,        // 建仓 40%
      "observe_days": 3,         // 观察 3 日
      "add_steps": 2,            // 最多加仓 2 档
      "add_weight": 0.3,         // 每档 +30%（总仓 ≤ 100%）
      "trigger": "medium_align"  // 触发：中期多头排列形成（仍可选 trend_up/new_high/above_ma5）
    }
  },
  "stop": { "stop_loss": 0.08, "trailing": 0.12 }   // 硬止损 8% + 移动止盈 12%
}
```

- **量化「沿 MA5 附近稳步推升」**：`launch.bias_range` 用乖离率约束「附近」；`slope_ma` + `above_ratio` 联合刻画「稳步推升」（仅乖离率不足以区分"稳步上行"与"贴 MA5 震荡"）。
- **校验约束**：`tiers` 须含 `role=entry`；`mas` 升序（短周期在前）；`init_weight + add_steps×add_weight ≤ 1`（总仓不超 100%）。
- 内置模板 `trend_pyramid` 即此范式，前端「模板库」可一键派生；编辑器以高层旋钮（乖离率上限/观察天数/加仓档数/移动止盈）暴露，均线阶梯固定。

### 4.5 代码式策略沙箱

- 执行隔离：在受限子进程中运行（独立内存/CPU/超时 limit，`resource`/`seccomp`/容器级限制）。
- 导入白名单：仅 `backtrader`、`numpy`、`pandas`、`math`、平台提供的 `Context/DataFeed` API；禁 `os`/`sys`/`socket`/`open`/`__import__` 等。
- 静态检查：AST 扫描禁用节点（import 非白名单、文件/网络/eval/exec）。
- 资源上限：CPU 时间、内存、运行墙钟超时；超限即杀。

### 4.6 参数寻优

- 网格/随机搜索：生成参数组合 → 批量 `run_backtest`（可用 vectorbt 加速纯向量化策略）→ 汇总指标表。
- **过拟合提示**：样本内/样本外（IS/OOS）拆分、参数平台稳定性、提示「最优解周围是否平滑」。

---

## 5. 因子研究引擎（M6）

### 5.1 因子计算

- 输入：因子定义（内置/表达式/代码）、股票池、区间。
- 表达式因子：受限表达式 DSL（基于 numpy/pandas，禁副作用），如 `rank(-pct_change(close, 20))`。
- 按交易日**截面**计算因子值，落 `factor_values`（PIT，按日分区）。

### 5.2 单因子检验（alphalens 风格，自实现以控口径）

```python
# app/core/engine/factor/analysis.py
def analyze_factor(factor_values: pd.DataFrame,   # index=(date,code) value
                   forward_returns: pd.DataFrame, # 未来 N 日收益
                   n_quantiles=5) -> FactorReport:
    # 1. RankIC：每日 spearman(factor, fwd_return)
    # 2. IC 序列 → ic_mean, ic_std, ic_ir = mean/std, ic_win_rate, IC 衰减(多周期)
    # 3. 分层：按因子值分 n 档，每档等权组合净值 + 单调性
    # 4. 多空组合：Top - Bottom 净值、年化、夏普
    # 5. 换手率：相邻调仓日分档变动
    ...
```

- 未来收益对齐严格防未来函数（`t` 日因子 vs `t→t+N` 收益）。
- 中性化：行业中性（用 `securities.board`/行业分类做哑变量回归取残差）、市值中性（对 log 市值回归）、去极值（MAD/分位截断）、标准化（z-score）。

### 5.3 多因子合成

- 标准化 + 中性化每个子因子 → 加权（等权 / IC 加权 / 历史 IC 衰减加权 / 回归法）→ 合成因子。
- 合成因子可写回 `factors`，并一键生成「因子选股策略」进入回测（§4.4 `factor_rank`）。

---

## 6. 执行引擎（M8，vnpy 风格）

### 6.1 架构

```
                ┌──────────────────────────────────────────┐
                │  ExecutionEngine（事件驱动）                │
                │  OrderRouter → RiskEngine(前置) → Gateway  │
                └───────┬───────────────────┬───────────────┘
              提交订单    │                   │ 行情/回报
                ┌────────▼──────┐    ┌───────▼─────────────┐
                │ PaperGateway  │    │ Broker Gateway(自托管)│
                │ (默认/线上)    │    │ XTP/tora/OST/EMT(vnpy)│
                └───────────────┘    └─────────────────────┘
```

### 6.2 Gateway 抽象

```python
class IGateway(Protocol):
    def connect(self, config: dict) -> None: ...
    def send_order(self, req: "OrderRequest") -> str: ...   # 返回 gateway_order_id
    def cancel_order(self, order_id: str) -> None: ...
    def query_account(self) -> "Account": ...
    def query_positions(self) -> list["Position"]: ...
    # 回报经事件回调：on_order / on_trade / on_account
```

- **PaperGateway**：用 DataFeed 收盘/次开行情 + A 股规则 + 成本模型撮合，**与回测口径一致**；维护虚拟资金/持仓/T+1 可用量；线上多租户主用。
- **券商网关（自托管）**：包一层 vnpy `BaseGateway` 适配（XTP/ToraStock/OST/EMT），把 vnpy 事件映射为本系统订单/成交/账户回报。**仅自托管 + 用户授权 + 合规** 启用（PRD §3.4）。

### 6.3 运行模式

1. **盘后调仓（默认低频）**：交易日盘后 `beat` 触发组合再平衡 → 用收盘信号生成次日订单 → 次日开盘经 Paper/券商执行。
2. **信号推送/跟单**：只生成调仓建议（买卖清单），经告警渠道推送，用户人工执行（公网合规友好）。
3. 订单状态机：`created → risk_check → submitted → (partial) → filled / canceled / rejected`，持久化到 `orders`/`trades`，断点可恢复。

---

## 7. 绩效分析引擎（M5）

基于 equity/trades 计算（`quantstats`/`empyrical-reloaded` + 自校口径）：

| 指标 | 口径 |
|------|------|
| 累计收益 | `nav[-1]/nav[0]-1` |
| 年化收益 | `(1+total)^(252/n_days)-1` |
| 年化波动 | `std(daily_ret)*sqrt(252)` |
| 夏普 | `(ann_ret - rf)/ann_vol`，rf 可配（默认 0）|
| 索提诺 | 用下行波动替代总波动 |
| 最大回撤 | `min(nav/cummax(nav)-1)`，记录起止日 |
| 卡玛 | `ann_ret / |max_drawdown|` |
| 胜率/盈亏比 | 由 trades 配对计算 |
| 换手率 | 日均成交额 / 平均市值 |
| Alpha/Beta | 对基准日收益回归 |
| 信息比率 | 超额收益均值 / 跟踪误差 |

报告渲染：Jinja2 模板 + ECharts/matplotlib 图 → HTML；PDF 经 weasyprint/playwright。月度收益表、回撤区间表、Top 贡献个股一并产出。

---

## 8. 风控引擎（M9）

### 8.1 接口

```python
@dataclass
class RiskDecision:
    allow: bool
    adjusted_qty: int | None = None     # 可被风控削减
    rule: str | None = None
    action: str | None = None           # reject|alert|liquidate
    reason: str | None = None

class RiskEngine:
    def __init__(self, rules: list["RiskRule"]): ...
    def check_order(self, order, ctx: "RiskContext") -> RiskDecision: ...   # 事前
    def check_portfolio(self, ctx) -> list["RiskAction"]: ...               # 事中（回撤/止损）
```

### 8.2 规则类型（可配置 params + action）

| 类型 | 说明 |
|------|------|
| `max_position_pct` | 单票市值占比上限 |
| `max_industry_pct` | 单行业暴露上限 |
| `max_count` | 最大持仓只数 |
| `max_order_amount` / `max_daily_amount` | 单笔/单日下单金额上限 |
| `blacklist` / `whitelist` | 黑/白名单 |
| `no_st` / `no_new` | 禁 ST / 新股 |
| `tradable` | 涨跌停/停牌不可交易（强制平台规则）|
| `stop_loss` / `take_profit` / `trailing_stop` | 个股止损/止盈/移动止损 |
| `max_drawdown` | 组合回撤熔断（停开仓/清仓）|

- 回测、仿真、实盘共用同一 `RiskEngine`；触发写 `risk_events` + 告警（M10）。
- 平台级强制规则（如 `tradable`、`no_st` 可选）由管理员设置，用户不可关闭关键项。

---

## 9. 测试与口径校验

- **黄金用例**：对每条 A 股规则（T+1/涨跌停/停牌/单位/成本）写确定性 fixture 用例（伪 DataFeed）。
- **回测=仿真口径一致性测试**：同策略同区间，回测结果与 Paper 逐日撮合结果一致。
- **因子 PIT 测试**：构造已知数据，校验 IC/分层数值与手算一致，验证无未来函数。
- **基准对比**：净值/夏普/回撤与 `quantstats` 交叉验证在容差内。

详见 [`BACKEND.md`](./BACKEND.md) §6 测试矩阵。

---

## 10. 扩展位

- 多频率：预留分钟级（data 服务已支持 `1m/5m/...`），引擎层可扩展。
- 多市场：DataFeed `market` 维度预留 H 股/美股。
- 引擎替换：`IBacktestEngine` 可接 vectorbt/zipline-reloaded；`IGateway` 可接更多券商。
- ML/AI 因子：因子层可接入机器学习打分模型（后续迭代）。

---

> 引擎实现遵循 TDD（口径用例先行）。框架版本（backtrader/vnpy）在 `pyproject.toml` 中锁定，升级需回归黄金用例。
