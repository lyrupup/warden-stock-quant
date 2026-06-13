# 守望者量化交易系统（Warden Stock Quant）

> 🦉 一套基于 **A 股日线级别行情** 的**低频量化研究与交易平台**：把「**策略 → 回测 → 分析 → 因子研究 → 仿真/实盘 → 仓位 → 风控 → 告警**」沉淀为统一、可扩展、多用户的量化闭环。
>
> 沿用守望者 **Scan · 侦查** 定位：让全市场行情成为可被策略与因子复用的可计算 alpha 底座。

---

## ✨ 项目由来

本项目灵感来源于 [`warden-stock-trending`](../warden-stock-trending)（早期把行情 + 策略 + 持仓 + 风控 + AI 耦合在一起的交易系统），并在 [`warden-stock-data`](../warden-stock-data)（A 股行情数据中台）之上构建。

- `warden-stock-data` 负责「**数据**」：只读、公共、可复用（日 K / 复权 / 指标 / 证券 / 交易日历）。
- 本项目是其**只读消费方**，专注「**研究与交易**」：策略回测、绩效分析、因子研究、仿真/实盘、仓位、风控、告警，并以**多用户 SaaS** 形态对外提供服务。

---

## 🧩 功能模块（M1–M11）

| 模块 | 能力 | 简介 |
|------|------|------|
| **M1** 用户与多租户 | 安全基座 | 注册/登录（JWT）、个人 API Key、角色、配额套餐、审计；严格租户隔离 |
| **M2** 行情数据接入与数据集 | 数据底座 | 对接 `warden-stock-data` 开放 API（HMAC）+ 导出文件导入；本地 PIT 数据集、交易日历、复权、DataFeed |
| **M3** 策略管理 | 策略 | 配置式（低代码）+ 代码式（沙箱）策略、版本管理、参数 schema、模板库 |
| **M4** 回测引擎 | 回测核心 | backtrader（抽象封装）+ A 股规则（T+1/涨跌停/停牌/单位）、成本模型、异步任务、可取消 |
| **M5** 绩效分析与报告 | 分析 | 年化/夏普/最大回撤/卡玛等指标、净值/回撤曲线、归因、HTML/PDF 报告、对比 |
| **M6** 量化因子研究 | 因子 | 因子库、按日 PIT 计算、IC/IR、分层回测、多因子合成 → 策略 |
| **M7** 仓位与组合管理 | 组合 | 组合定义、目标权重、再平衡、持仓/资金跟踪 |
| **M8** 仿真/实盘交易 | 执行 | vnpy 风格执行内核 + 可插拔网关（默认 Paper，券商网关自托管合规）、信号推送 |
| **M9** 风险控制 | 风控 | 事前/事中/事后规则引擎（仓位/暴露/回撤/止损），回测与实盘共用 |
| **M10** 日志告警监控 | 可观测 | 结构化日志、审计、任务监控、告警渠道（邮件/Webhook/钉钉/飞书）|
| **M11** Web 控制台 | 界面 | React 可视化：策略/回测报告/因子/组合/交易/风控/告警/运维 |

---

## 🏛️ 系统架构

```
前端控制台（React）──REST /api/v1（JWT / API Key）──► FastAPI（api，无状态）
                                                        │ 投递任务（Celery + Redis）
                                                        ▼
                              worker：回测(backtrader) / 因子(pandas) / 数据同步 / 交易执行(vnpy)
                                                        │
                              DataFeed（PIT）◄── 本地数据集（PostgreSQL / Parquet）
                                                        ▲
                              HMAC 客户端 / 文件导入 ──► warden-stock-data（只读行情 API + 导出文件）
   存储：PostgreSQL（业务 + 数据集）+ Redis（缓存/队列/限流/锁）+ 文件存储（报告）
   贯穿：日志 / 审计 / 告警 / 监控（M10）
```

---

## 📐 技术栈

> 本项目后端以 **Python** 为权威实现（量化生态 backtrader/vnpy/pandas/alphalens 均在 Python，且为明确要求）。这是针对量化计算特性、在 `AGENTS.md` 通用技术表之上的项目级特化，理由见 `docs/BACKEND.md` §1。

- **后端**：Python 3.11 + FastAPI + SQLAlchemy 2.0/Alembic + Pydantic v2 + Celery/Redis；JWT/OAuth2 + API Key 鉴权；TDD（pytest）测试先行。
- **量化引擎**：backtrader（回测，抽象封装）、vnpy（仿真/实盘执行 + 网关）、pandas/numpy/scipy/statsmodels、quantstats/empyrical（绩效）、alphalens 风格因子分析；可选 vectorbt（寻优）/ zipline-reloaded（研究）。
- **数据接入**：httpx HMAC 客户端消费 `warden-stock-data` `/open/v1/*`；pyarrow 导入导出文件；数据集落 PostgreSQL（+可选 Parquet 列存）。
- **存储**：PostgreSQL + Redis + 文件/对象存储。
- **前端**：React + Vite + shadcn/ui + Tailwind CSS；ky + TanStack Query；zustand；ECharts/lightweight-charts；Monaco。
- **部署**：Docker + docker-compose（postgres / redis / api / worker / beat / frontend）；PostgreSQL 数据 bind mount 到 `backend/deploy/pgdata`（入 `.gitignore`）；镜像名带项目前缀 `warden-stock-quant-*`。

---

## 📚 文档索引

| 文档 | 路径 | 用途 |
|------|------|------|
| 需求文档（PRD）| [`docs/PRD.md`](docs/PRD.md) | 系统功能、角色、M1–M11 模块、数据模型、里程碑 |
| 后端技术文档 | [`docs/BACKEND.md`](docs/BACKEND.md) | FastAPI 架构、分层、DB schema、任务队列、API、TDD、部署 |
| 量化引擎设计 | [`docs/QUANT_ENGINE.md`](docs/QUANT_ENGINE.md) | 回测/因子/执行/风控/绩效引擎内部设计 |
| 行情数据接入 | [`docs/DATA_ACCESS.md`](docs/DATA_ACCESS.md) | 对接 data 服务开放 API + 文件导入 + 本地数据集 |
| 前端技术文档 | [`docs/FRONTEND.md`](docs/FRONTEND.md) | React 控制台架构、页面、契约对齐 |
| 接口契约 | [`docs/openapi.yaml`](docs/openapi.yaml) | API 契约（权威）|

---

## ⚠️ 合规与免责

- 真实 A 股程序化交易有强合规门槛（专业投资者认证 + 券商三方系统采购 + 券商内网托管）。**公网多租户形态仅提供仿真/纸面交易与信号推送**，真实资金自动下单仅在自托管单租户合规部署下可用（详见 `docs/PRD.md` §3.4）。
- 本系统仅供量化研究与交易辅助，**不构成任何投资建议**；据此操作风险自负。

---

## 🚀 快速开始（规划中）

```bash
# 后端
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
docker compose -f deploy/docker-compose.dev.yml up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload --port 8000
celery -A app.tasks.celery_app worker -Q backtest,factor,data,trade -l info
celery -A app.tasks.celery_app beat -l info

# 前端
cd frontend && pnpm install && pnpm dev
```

---

> 任一核心功能变更须同步更新 `README.md` 与 `docs/*`，并以 `openapi.yaml` 为接口权威（见 `AGENTS.md`）。
