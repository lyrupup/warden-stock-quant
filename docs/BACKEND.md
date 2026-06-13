# 守望者量化交易系统 · 后端技术开发文档

> Warden Stock Quant · Backend Engineering Doc
>
> 前置阅读：[`PRD.md`](./PRD.md)。引擎细节见 [`QUANT_ENGINE.md`](./QUANT_ENGINE.md)，数据接入见 [`DATA_ACCESS.md`](./DATA_ACCESS.md)，接口契约以 [`openapi.yaml`](./openapi.yaml) 为准。
>
> 开发遵循 `AGENTS.md`：TDD 测试先行；中间件封装鉴权/日志/CORS/限流/超时；Docker 编排；环境变量注入。

---

## 1. 技术栈与架构

### 1.1 技术选型与「为何用 Python」

`AGENTS.md` 通用技术表中「核心后端服务」推荐 Go + Gin + GORM。**本项目针对量化计算特性做项目级特化，后端以 Python 为权威实现**，理由：

1. 量化生态几乎全在 Python：**backtrader**（回测）、**vnpy**（实盘/执行）、pandas/numpy/scipy/statsmodels、`alphalens-reloaded`、`quantstats`、`empyrical-reloaded`、vectorbt、zipline-reloaded。用 Go 需大量自研或跨语言桥接，得不偿失。
2. 用户明确要求 Python 后台。
3. `warden-stock-data` 已有 Python quant 服务先例，团队对该栈不陌生。

| 层 | 选型 | 说明 |
|----|------|------|
| 语言/运行时 | Python 3.11 | 类型注解 + asyncio |
| Web 框架 | **FastAPI** + uvicorn(+gunicorn) | 异步、自动 OpenAPI、Pydantic 校验 |
| 数据校验/序列化 | **Pydantic v2** | DTO / Schema / Settings |
| ORM / 迁移 | **SQLAlchemy 2.0**（async）+ **Alembic** | 业务表 + 数据集表 |
| 任务队列 | **Celery** + Redis（broker/backend）| 回测/因子/同步/交易长任务 |
| 定时调度 | **Celery beat**（或 APScheduler）| 盘后数据同步、组合再平衡、因子计算 |
| 缓存/锁/限流 | **Redis** | 缓存、分布式锁、限流、nonce、配额计数 |
| 主数据库 | **PostgreSQL 16** | 业务数据 + 本地行情数据集 |
| 列存（可选） | Parquet(pyarrow) / DuckDB | 大规模因子/回测数据加速 |
| 回测引擎 | **backtrader**（抽象封装）| 主引擎；预留 vectorbt/zipline-reloaded |
| 执行引擎 | **vnpy** 风格内核 + Gateway | PaperGateway 默认；券商网关自托管 |
| 数据分析 | pandas/numpy/scipy/statsmodels/quantstats | 绩效与因子分析 |
| HTTP 客户端 | **httpx** | 消费 warden-stock-data 开放 API（HMAC）|
| 鉴权 | JWT（python-jose）+ passlib(argon2) | OAuth2 Password + API Key |
| 沙箱 | RestrictedPython / 子进程隔离 + 资源限制 | 代码式策略执行 |
| 日志 | structlog（JSON）| 结构化日志 + trace_id |
| 监控 | prometheus-client + /healthz | 指标与健康检查 |
| 测试 | pytest + pytest-asyncio + httpx | TDD |

### 1.2 进程拓扑（重要）

后端是**单代码库、多进程角色**：

```
┌────────────┐   REST /api/v1    ┌──────────────────────────┐
│  Frontend  │ ────────────────► │  api（FastAPI / uvicorn）  │  无状态，可水平扩展
└────────────┘                   └────────┬─────────────────┘
                                          │ 投递任务(Celery)
                                ┌─────────▼──────────┐
                                │   Redis（broker）   │
                                └─────────┬──────────┘
        ┌─────────────────────────────────┼───────────────────────────────┐
        ▼                                  ▼                               ▼
┌────────────────┐              ┌────────────────────┐         ┌──────────────────┐
│ worker-backtest│              │ worker-factor      │         │ worker-data/trade│
│ (backtrader)   │              │ (pandas/alphalens) │         │ (同步/执行/调度)   │
└───────┬────────┘              └─────────┬──────────┘         └────────┬─────────┘
        └───────────────┬─────────────────┴───────────────────┬─────────┘
                        ▼                                      ▼
                 ┌─────────────┐                       ┌──────────────────────┐
                 │ PostgreSQL  │                       │ warden-stock-data API │
                 └─────────────┘                       └──────────────────────┘
        ┌────────────┐
        │ beat（定时）│  盘后同步 / 再平衡 / 因子计算
        └────────────┘
```

- **api**：仅处理 HTTP（CRUD、提交任务、查询结果），不跑重计算。
- **worker**：按队列分角色（`backtest` / `factor` / `data` / `trade`），可独立扩缩容；回测进程隔离防串扰。
- **beat**：定时投递（交易日历感知）。
- **执行引擎**：仿真常驻或按调度运行；实盘网关（自托管）由专用 worker/常驻进程承载。

### 1.3 分层架构

严格遵循 `core/`（可移植核心）与 `features/`（业务模块）划分：

```
请求 → router(features) → service(features) → repository/core → DB/外部
                              │
                              └→ 提交 Celery task → engine(core) → repository
```

- **router**：路由 + 依赖注入（当前用户、DB session）+ DTO 校验，不含业务逻辑。
- **service**：业务编排、事务、权限作用域、配额校验。
- **repository**：数据访问（SQLAlchemy），仅此层接触 ORM。
- **core engine**：回测/因子/执行/风控/数据访问等可移植核心，**不依赖 FastAPI**（便于在 worker/CLI 复用与单测）。
- **schema(Pydantic)**：请求/响应 DTO，与 ORM 模型分离。

### 1.4 目录结构

```
backend/
├── app/
│   ├── main.py                  # FastAPI 装配（中间件/路由/生命周期）
│   ├── core/                    # 可移植核心（不依赖 Web）
│   │   ├── config/              # Settings(Pydantic) / 环境变量
│   │   ├── db/                  # engine, session, base, alembic env
│   │   ├── security/            # JWT, 密码哈希, API Key, RBAC, 沙箱
│   │   ├── cache/               # Redis 客户端, 锁, 限流, 配额
│   │   ├── logging/             # structlog 配置, trace 中间件
│   │   ├── errors/              # 统一异常 + 错误码
│   │   ├── response/            # 统一响应包装
│   │   ├── data/                # DataFeed 抽象 + 数据集访问（见 DATA_ACCESS）
│   │   │   ├── client/          #   warden-stock-data HMAC 客户端
│   │   │   ├── feed/            #   DataFeed（回测/因子/实盘统一取数）
│   │   │   └── importer/        #   导出文件导入
│   │   ├── engine/              # 量化引擎（见 QUANT_ENGINE）
│   │   │   ├── backtest/        #   IBacktestEngine + backtrader 实现
│   │   │   ├── factor/          #   因子计算 + IC/分层
│   │   │   ├── execution/       #   vnpy 风格执行 + Gateway
│   │   │   ├── risk/            #   风控规则引擎
│   │   │   └── analytics/       #   绩效指标 + 报告
│   │   └── alerting/            # 告警渠道适配（email/webhook/钉钉/飞书）
│   ├── features/                # 业务模块（每个含 router/service/repo/schema/models）
│   │   ├── auth/                # M1 登录/注册/JWT/API Key
│   │   ├── users/               # M1 用户/角色/配额/套餐
│   │   ├── datasets/            # M2 数据集/同步作业
│   │   ├── strategies/          # M3 策略/版本/模板
│   │   ├── backtests/           # M4 回测任务/结果
│   │   ├── reports/             # M5 报告/对比/导出
│   │   ├── factors/             # M6 因子/计算/分析
│   │   ├── portfolios/          # M7 组合/再平衡/持仓
│   │   ├── trading/             # M8 仿真/实盘/订单/账户
│   │   ├── risk/                # M9 风控规则/事件
│   │   ├── alerts/              # M10 告警渠道/告警
│   │   └── admin/               # 运维：数据源凭证/配额/审计/监控
│   ├── tasks/                   # Celery 任务定义（按队列）
│   │   ├── celery_app.py
│   │   ├── backtest_tasks.py
│   │   ├── factor_tasks.py
│   │   ├── data_tasks.py
│   │   └── trade_tasks.py
│   └── api/                     # 路由聚合 + 版本前缀 /api/v1
├── tests/                       # pytest（unit / integration / engine 口径）
├── alembic/                     # 迁移脚本
├── deploy/
│   ├── docker-compose.yml
│   ├── Dockerfile
│   └── pgdata/                  # PostgreSQL bind mount（.gitignore）
├── pyproject.toml               # 依赖与工具（ruff/mypy/pytest）
├── .env.example
└── README.md
```

> 命名遵循 `AGENTS.md`：功能目录 kebab-case（Python 包用 snake_case 模块），具名导出；Python 侧用类型注解与 dataclass/Pydantic，不强制 TS 的 `T/E/I` 前缀。

### 1.5 统一响应与错误码

所有接口返回统一结构（与 data 服务保持一致风格）：

```json
{ "code": 0, "message": "ok", "data": {} }
```

- `code=0` 成功；非 0 为业务错误码；分页 `data = { "list": [], "total": 0, "page": 1, "size": 20 }`。
- HTTP 状态码与业务 `code` 并存（HTTP 表达传输语义，`code` 表达业务语义）。

**错误码表**

| code | HTTP | 含义 |
|------|------|------|
| 0 | 200 | 成功 |
| 10001 | 400 | 参数错误 |
| 10002 | 404 | 资源不存在 |
| 10003 | 409 | 资源冲突（重名/状态冲突）|
| 10408 | 408 | 请求/任务超时 |
| 40101 | 401 | 未认证 / token 失效 |
| 40102 | 401 | API Key 无效 / 已吊销 |
| 40301 | 403 | 越权（非本租户资源）|
| 40302 | 403 | 角色权限不足 |
| 40303 | 403 | 实盘未授权 |
| 42901 | 429 | 触发限流（QPS）|
| 42902 | 429 | 超出配额（回测/因子/存储）|
| 50001 | 500 | 服务内部错误 |
| 52001 | 502 | 上游 warden-stock-data 异常（已降级/重试）|
| 60001 | 200 | 任务已入队（异步）|
| 61001 | 422 | 策略沙箱校验失败 |
| 62001 | 422 | 风控拦截（下单被拒）|

### 1.6 数值精度约定（重要）

- 来自 data 服务的价格/比率/指标为 **decimal 字符串**（如 `"10.5000"`）；入库与计算前转 `Decimal` 或 `float64`（回测内部用 `Decimal` 处理现金/成交，统计分析用 `float`）。
- 资金、持仓、成交金额用 `Numeric(20,4)`（PG）/ `Decimal`；收益率/指标用 `Numeric(20,8)`。
- 对外序列化金额/比率统一为 decimal 字符串，避免 JSON 浮点误差。

---

## 2. 鉴权与权限设计

### 2.1 用户鉴权（JWT / OAuth2 Password）

- 登录 `POST /api/v1/auth/login` → 返回 `access_token`（短期，如 30min）+ `refresh_token`（长期，如 7d）。
- `Authorization: Bearer <access_token>`；过期用 `refresh_token` 换新。
- 密码 argon2 哈希；登录失败计数限速（Redis）。
- JWT payload：`sub=user_id, role, plan, exp, jti`；`jti` 可加入黑名单实现登出。

### 2.2 API Key（程序化访问）

- 用户创建 API Key：返回 `key = prefix + secret`，**仅此一次明文**，库内存 `argon2(secret)` 与 `prefix`。
- 请求头 `Authorization: Bearer wsq_<prefix>_<secret>`；服务端按 prefix 查记录校验 secret。
- API Key 设 `scopes`（`read` / `backtest` / `factor` / `trade`）与独立配额；越 scope `403`。

### 2.3 RBAC 与租户作用域

- 依赖注入 `get_current_user()` 解析身份；`require_role("admin")` 守护管理路由。
- **租户作用域强制**：repository 层所有查询带 `where user_id = :current_user`；service 层校验资源 owner，越权 `40301`。
- 管理员审计访问用户私有资源时写 `audit_log`。

### 2.4 路由分组与权限边界

| 前缀 | 鉴权 | 说明 |
|------|------|------|
| `/api/v1/auth/*` | 公开/部分 | 注册、登录、刷新 |
| `/api/v1/*` | 用户 JWT / API Key | 业务接口（按租户隔离）|
| `/api/v1/admin/*` | 管理员 JWT | 用户/配额/数据源凭证/告警渠道/监控/审计 |
| `/healthz`、`/metrics` | 内网/公开只读 | 健康检查、指标 |

### 2.5 warden-stock-data 数据源凭证（平台托管）

- `secretId/secretKey` 由管理员在 `/api/v1/admin/data-source` 配置，**`secretKey` 加密存储**（`CONFIG_ENC_KEY` 对称加密），运行时解密用于 HMAC 签名（见 `DATA_ACCESS.md`）。
- 用户不接触凭证，所有行情访问经平台 DataFeed 间接获取。

---

## 3. 数据库设计

### 3.1 设计约定

- 主键 `id BIGSERIAL`（或 ULID）；统一 `created_at/updated_at`（timestamptz）；软删除用 `deleted_at`（按需）。
- 多租户表均含 `user_id` 外键 + 索引；金额 `numeric(20,4)`，比率/指标 `numeric(20,8)`。
- JSON 配置用 `jsonb`；枚举用 `varchar + CHECK` 或独立小表。
- 数据集表（行情）与业务表可同库不同 schema（`market` schema vs `app` schema）。

### 3.2 ER 概览

```
app schema:
  users ──< api_keys
  users ──< strategies ──< strategy_versions
  users ──< backtests >── strategy_versions
  backtests ──< backtest_trades ; ──< backtest_daily_positions ; ──1 backtest_metrics
  users ──< factors ──< factor_versions ; factors ──< factor_values ; ──< factor_analyses
  users ──< portfolios ──< portfolio_target_weights ; ──< positions ; ──< orders ──< trades
  users ──< risk_rule_sets ──< risk_rules ; users ──< risk_events
  users ──< alert_channels ; users ──< alerts
  users ──< quotas ; plans
  audit_logs ; system_jobs（任务总表）
  data_source_credentials（admin）

market schema（本地数据集，见 DATA_ACCESS）:
  securities ; daily_bars ; adjust_factors ; trading_calendar ; indicator_snapshots ; data_sync_jobs
```

### 3.3 核心表结构（DDL 摘要）

```sql
-- ===== M1 用户与租户 =====
CREATE TABLE users (
  id            BIGSERIAL PRIMARY KEY,
  email         VARCHAR(190) UNIQUE NOT NULL,
  username      VARCHAR(64)  UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role          VARCHAR(16)  NOT NULL DEFAULT 'user',   -- user | admin
  plan          VARCHAR(32)  NOT NULL DEFAULT 'free',
  status        VARCHAR(16)  NOT NULL DEFAULT 'active',  -- active | disabled
  live_enabled  BOOLEAN      NOT NULL DEFAULT false,     -- 实盘授权开关
  created_at    TIMESTAMPTZ  NOT NULL DEFAULT now(),
  updated_at    TIMESTAMPTZ  NOT NULL DEFAULT now()
);

CREATE TABLE api_keys (
  id          BIGSERIAL PRIMARY KEY,
  user_id     BIGINT NOT NULL REFERENCES users(id),
  name        VARCHAR(64),
  prefix      VARCHAR(16) UNIQUE NOT NULL,
  key_hash    VARCHAR(255) NOT NULL,          -- argon2(secret)
  scopes      VARCHAR(128) NOT NULL DEFAULT 'read',
  qps_limit   INT, daily_quota INT,
  status      VARCHAR(16) NOT NULL DEFAULT 'active',  -- active | revoked
  last_used_at TIMESTAMPTZ,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE plans (
  code VARCHAR(32) PRIMARY KEY,            -- free | pro | ...
  name VARCHAR(64),
  limits JSONB NOT NULL                    -- {max_concurrent_backtests, max_universe, max_range_days, ...}
);
CREATE TABLE quotas (                       -- 用户级配额用量
  user_id BIGINT PRIMARY KEY REFERENCES users(id),
  usage   JSONB NOT NULL DEFAULT '{}',     -- {backtests_today, storage_bytes, ...}
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ===== M3 策略 =====
CREATE TABLE strategies (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  name VARCHAR(128) NOT NULL,
  type VARCHAR(16) NOT NULL DEFAULT 'config', -- config | code
  description TEXT,
  latest_version INT NOT NULL DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(user_id, name)
);
CREATE INDEX idx_strategies_user ON strategies(user_id);

CREATE TABLE strategy_versions (
  id BIGSERIAL PRIMARY KEY,
  strategy_id BIGINT NOT NULL REFERENCES strategies(id),
  version INT NOT NULL,
  params_schema JSONB,         -- 可调参数定义
  default_params JSONB,
  config JSONB,                -- config 式：信号积木配置
  code TEXT,                   -- code 式：backtrader Strategy 源码
  universe JSONB,              -- 股票池定义
  created_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE(strategy_id, version)
);

-- ===== M4 回测 =====
CREATE TABLE backtests (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  strategy_version_id BIGINT NOT NULL REFERENCES strategy_versions(id),
  name VARCHAR(128),
  params JSONB, universe JSONB,
  date_from DATE NOT NULL, date_to DATE NOT NULL,
  init_capital NUMERIC(20,4) NOT NULL,
  benchmark VARCHAR(16) DEFAULT '000300',
  cost_config JSONB,           -- 佣金/印花税/滑点
  adjust VARCHAR(8) DEFAULT 'qfq',
  status VARCHAR(16) NOT NULL DEFAULT 'queued', -- queued|running|succeeded|failed|canceled
  progress NUMERIC(5,2) DEFAULT 0,
  job_id VARCHAR(64),          -- celery task id
  error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(), finished_at TIMESTAMPTZ
);
CREATE INDEX idx_backtests_user ON backtests(user_id, created_at DESC);

CREATE TABLE backtest_metrics (
  backtest_id BIGINT PRIMARY KEY REFERENCES backtests(id) ON DELETE CASCADE,
  total_return NUMERIC(20,8), annual_return NUMERIC(20,8),
  volatility NUMERIC(20,8), sharpe NUMERIC(20,8), sortino NUMERIC(20,8),
  calmar NUMERIC(20,8), max_drawdown NUMERIC(20,8), mdd_from DATE, mdd_to DATE,
  win_rate NUMERIC(20,8), profit_factor NUMERIC(20,8), turnover NUMERIC(20,8),
  alpha NUMERIC(20,8), beta NUMERIC(20,8), info_ratio NUMERIC(20,8),
  extra JSONB
);

-- 净值/交易/持仓：高频写，可走列存或大表分区
CREATE TABLE backtest_equity (        -- 每日净值
  backtest_id BIGINT REFERENCES backtests(id) ON DELETE CASCADE,
  trade_date DATE, nav NUMERIC(20,8), benchmark_nav NUMERIC(20,8),
  drawdown NUMERIC(20,8), cash NUMERIC(20,4), market_value NUMERIC(20,4),
  PRIMARY KEY(backtest_id, trade_date)
);
CREATE TABLE backtest_trades (
  id BIGSERIAL PRIMARY KEY,
  backtest_id BIGINT REFERENCES backtests(id) ON DELETE CASCADE,
  trade_date DATE, code VARCHAR(16), side VARCHAR(4),  -- buy|sell
  price NUMERIC(20,4), qty INT, amount NUMERIC(20,4),
  commission NUMERIC(20,4), tax NUMERIC(20,4), pnl NUMERIC(20,4)
);
CREATE INDEX idx_bt_trades ON backtest_trades(backtest_id, trade_date);
CREATE TABLE backtest_daily_positions (
  backtest_id BIGINT REFERENCES backtests(id) ON DELETE CASCADE,
  trade_date DATE, code VARCHAR(16), qty INT,
  price NUMERIC(20,4), market_value NUMERIC(20,4), weight NUMERIC(20,8),
  PRIMARY KEY(backtest_id, trade_date, code)
);

-- ===== M6 因子 =====
CREATE TABLE factors (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  name VARCHAR(128) NOT NULL, category VARCHAR(32),
  type VARCHAR(16) DEFAULT 'expr',  -- expr | code | builtin
  expr TEXT, code TEXT, params JSONB,
  direction SMALLINT DEFAULT 1,     -- 1 越大越好 / -1 越小越好
  created_at TIMESTAMPTZ DEFAULT now(), UNIQUE(user_id, name)
);
CREATE TABLE factor_values (         -- PIT 因子值（大表，按 trade_date 分区）
  factor_id BIGINT REFERENCES factors(id) ON DELETE CASCADE,
  code VARCHAR(16), trade_date DATE, value NUMERIC(20,8),
  PRIMARY KEY(factor_id, code, trade_date)
) PARTITION BY RANGE (trade_date);
CREATE TABLE factor_analyses (
  id BIGSERIAL PRIMARY KEY,
  factor_id BIGINT REFERENCES factors(id) ON DELETE CASCADE,
  date_from DATE, date_to DATE, universe JSONB, forward_period INT, n_quantiles INT,
  ic_mean NUMERIC(20,8), ic_ir NUMERIC(20,8), ic_win_rate NUMERIC(20,8),
  quantile_returns JSONB, ic_series JSONB, turnover JSONB,
  status VARCHAR(16) DEFAULT 'queued', job_id VARCHAR(64),
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ===== M7 组合 / M8 交易 =====
CREATE TABLE portfolios (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL REFERENCES users(id),
  name VARCHAR(128) NOT NULL,
  mode VARCHAR(8) NOT NULL DEFAULT 'paper',  -- paper | live
  strategy_version_id BIGINT REFERENCES strategy_versions(id),
  init_capital NUMERIC(20,4), cash NUMERIC(20,4),
  benchmark VARCHAR(16) DEFAULT '000300',
  rebalance VARCHAR(8) DEFAULT 'day',         -- day|week|month
  weight_scheme JSONB, risk_rule_set_id BIGINT,
  status VARCHAR(16) DEFAULT 'active',
  created_at TIMESTAMPTZ DEFAULT now(), UNIQUE(user_id, name)
);
CREATE TABLE positions (
  id BIGSERIAL PRIMARY KEY,
  portfolio_id BIGINT REFERENCES portfolios(id) ON DELETE CASCADE,
  code VARCHAR(16), qty INT, avail_qty INT,     -- avail_qty 处理 T+1
  cost NUMERIC(20,4), last_price NUMERIC(20,4),
  market_value NUMERIC(20,4), pnl NUMERIC(20,4),
  updated_at TIMESTAMPTZ DEFAULT now(), UNIQUE(portfolio_id, code)
);
CREATE TABLE orders (
  id BIGSERIAL PRIMARY KEY,
  user_id BIGINT NOT NULL, portfolio_id BIGINT REFERENCES portfolios(id),
  code VARCHAR(16), side VARCHAR(4), order_type VARCHAR(8) DEFAULT 'limit',
  price NUMERIC(20,4), qty INT, filled_qty INT DEFAULT 0,
  status VARCHAR(16) DEFAULT 'created',  -- created|risk_rejected|submitted|partial|filled|canceled|rejected
  gateway VARCHAR(16) DEFAULT 'paper', gateway_order_id VARCHAR(64),
  reason TEXT, trade_date DATE,
  created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE trades (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT REFERENCES orders(id), portfolio_id BIGINT,
  code VARCHAR(16), side VARCHAR(4), price NUMERIC(20,4), qty INT,
  amount NUMERIC(20,4), commission NUMERIC(20,4), tax NUMERIC(20,4),
  trade_time TIMESTAMPTZ DEFAULT now()
);

-- ===== M9 风控 =====
CREATE TABLE risk_rule_sets (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT NOT NULL,
  name VARCHAR(128), scope VARCHAR(16) DEFAULT 'portfolio', is_platform BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE risk_rules (
  id BIGSERIAL PRIMARY KEY, rule_set_id BIGINT REFERENCES risk_rule_sets(id) ON DELETE CASCADE,
  type VARCHAR(32),               -- max_position_pct|max_industry_pct|stop_loss|max_drawdown|blacklist|...
  params JSONB, action VARCHAR(16) DEFAULT 'reject',  -- reject|alert|liquidate
  enabled BOOLEAN DEFAULT true
);
CREATE TABLE risk_events (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT, portfolio_id BIGINT, order_id BIGINT,
  rule_type VARCHAR(32), action VARCHAR(16), detail JSONB,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- ===== M10 告警 / 审计 / 任务 =====
CREATE TABLE alert_channels (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT, scope VARCHAR(16) DEFAULT 'user',
  type VARCHAR(16),               -- email|webhook|dingtalk|feishu|serverchan
  config JSONB, enabled BOOLEAN DEFAULT true
);
CREATE TABLE alerts (
  id BIGSERIAL PRIMARY KEY, user_id BIGINT, level VARCHAR(8), source VARCHAR(32),
  title VARCHAR(255), body TEXT, dedup_key VARCHAR(190), sent BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE audit_logs (
  id BIGSERIAL PRIMARY KEY, actor_id BIGINT, actor_role VARCHAR(16),
  action VARCHAR(64), target_type VARCHAR(32), target_id VARCHAR(64),
  ip VARCHAR(64), detail JSONB, created_at TIMESTAMPTZ DEFAULT now()
);
CREATE TABLE system_jobs (          -- 任务总表（统一查询进度）
  id VARCHAR(64) PRIMARY KEY,       -- celery id
  user_id BIGINT, type VARCHAR(32), -- backtest|factor|data_sync|rebalance|trade
  ref_id BIGINT, status VARCHAR(16), progress NUMERIC(5,2),
  payload JSONB, result JSONB, error TEXT,
  created_at TIMESTAMPTZ DEFAULT now(), updated_at TIMESTAMPTZ DEFAULT now()
);

-- ===== 数据源凭证（admin）=====
CREATE TABLE data_source_credentials (
  id BIGSERIAL PRIMARY KEY, name VARCHAR(64), base_url VARCHAR(255),
  secret_id VARCHAR(128), secret_key_enc TEXT,   -- 对称加密存储
  qps_limit INT, daily_quota INT, enabled BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

> `market` schema（`securities`/`daily_bars`/`adjust_factors`/`trading_calendar`/`indicator_snapshots`/`data_sync_jobs`）DDL 见 [`DATA_ACCESS.md`](./DATA_ACCESS.md)。

### 3.4 SQLAlchemy 模型示例

```python
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, BigInteger, ForeignKey, Numeric
from app.core.db.base import Base

class Backtest(Base):
    __tablename__ = "backtests"
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    strategy_version_id: Mapped[int] = mapped_column(ForeignKey("strategy_versions.id"))
    status: Mapped[str] = mapped_column(String(16), default="queued")
    progress: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    # ...
    metric: Mapped["BacktestMetric"] = relationship(back_populates="backtest", uselist=False)
```

---

## 4. API 接口设计

### 4.1 通用约定

- BasePath：`/api/v1`；统一响应（§1.5）；分页 `?page=&size=`；排序 `?sort=field,-field2`。
- 异步资源（回测/因子/同步）走「**提交→轮询**」：`POST` 创建返回 `job_id` + 资源 id（`code=60001`），`GET .../{id}` 查状态与进度，`GET .../{id}/result` 取结果。
- 所有写操作记审计（关键操作）。

### 4.2 接口总览（详见 openapi.yaml）

| 模块 | 方法 | 路径 | 说明 |
|------|------|------|------|
| Auth | POST | `/api/v1/auth/register` | 注册 |
| Auth | POST | `/api/v1/auth/login` | 登录（JWT）|
| Auth | POST | `/api/v1/auth/refresh` | 刷新 token |
| Auth | GET | `/api/v1/me` | 当前用户信息/配额 |
| ApiKey | GET/POST/DELETE | `/api/v1/api-keys[/{id}]` | API Key 管理（创建一次性返回）|
| Datasets | GET | `/api/v1/datasets/status` | 数据集新鲜度/缺口 |
| Datasets | POST | `/api/v1/datasets/sync` | 触发同步（管理员/有权用户）|
| Datasets | GET | `/api/v1/market/securities` `/calendar` `/bars` | 经平台读行情（DataFeed 代理）|
| Strategies | CRUD | `/api/v1/strategies[/{id}]` | 策略 |
| Strategies | POST/GET | `/api/v1/strategies/{id}/versions` | 版本 |
| Strategies | GET | `/api/v1/strategy-templates` | 模板库 |
| Strategies | POST | `/api/v1/strategies/{id}/validate` | 沙箱/配置校验 |
| Backtests | POST | `/api/v1/backtests` | 创建回测（异步）|
| Backtests | GET | `/api/v1/backtests[/{id}]` | 列表/详情/进度 |
| Backtests | GET | `/api/v1/backtests/{id}/equity` `/trades` `/positions` `/metrics` | 结果分片 |
| Backtests | POST | `/api/v1/backtests/{id}/cancel` | 取消 |
| Backtests | POST | `/api/v1/optimizations` | 参数寻优（批量回测）|
| Reports | GET | `/api/v1/backtests/{id}/report` | 报告（html/pdf）|
| Reports | POST | `/api/v1/reports/compare` | 多回测对比 |
| Reports | POST | `/api/v1/backtests/{id}/share` | 生成分享链接 |
| Factors | CRUD | `/api/v1/factors[/{id}]` | 因子 |
| Factors | POST | `/api/v1/factors/{id}/compute` | 计算因子值（异步）|
| Factors | POST | `/api/v1/factors/{id}/analyze` | IC/分层分析（异步）|
| Factors | GET | `/api/v1/factors/{id}/analyses/{aid}` | 分析结果 |
| Factors | POST | `/api/v1/factors/combine` | 多因子合成 |
| Portfolios | CRUD | `/api/v1/portfolios[/{id}]` | 组合 |
| Portfolios | GET | `/api/v1/portfolios/{id}/positions` | 持仓 |
| Portfolios | POST | `/api/v1/portfolios/{id}/rebalance` | 触发再平衡（生成订单）|
| Trading | GET/POST | `/api/v1/portfolios/{id}/orders` | 订单（列表/手动下单）|
| Trading | POST | `/api/v1/orders/{id}/cancel` | 撤单 |
| Trading | GET | `/api/v1/portfolios/{id}/trades` | 成交 |
| Risk | CRUD | `/api/v1/risk/rule-sets[/{id}]` | 风控规则集 |
| Risk | GET | `/api/v1/risk/events` | 风控事件 |
| Alerts | CRUD | `/api/v1/alerts/channels[/{id}]` | 告警渠道 |
| Alerts | GET | `/api/v1/alerts` | 告警记录 |
| Jobs | GET | `/api/v1/jobs[/{id}]` | 任务统一查询 |
| Admin | CRUD | `/api/v1/admin/users[/{id}]` | 用户/角色/配额/实盘授权 |
| Admin | CRUD | `/api/v1/admin/data-source` | data 服务凭证 |
| Admin | CRUD | `/api/v1/admin/plans` | 套餐配额 |
| Admin | GET | `/api/v1/admin/audit-logs` `/system/jobs` `/metrics` | 审计/任务/监控 |
| Sys | GET | `/healthz` `/metrics` | 健康/指标 |

---

## 5. 核心功能模块设计（后端视角）

> 引擎内部细节见 `QUANT_ENGINE.md`，此处给出 service 编排与任务划分。

### M1 用户与租户
- `auth/service.py`：注册（校验邮箱唯一）、登录（验密 + 限速 + 发 token）、刷新、登出（jti 黑名单）。
- `users/service.py`：资料、API Key（生成→哈希存储→一次性返回）、配额读取。
- 中间件：`AuthMiddleware`（解析 JWT/API Key）、`TenantScope`（注入 user_id）、`RateLimit`、`Audit`。

### M2 数据接入（详见 DATA_ACCESS）
- `datasets/service.py`：触发同步任务、查新鲜度/缺口；`market` 只读代理（DataFeed）。
- `data_tasks.py`：`sync_securities` / `sync_daily_bars` / `sync_indicators` / `import_export_file`（幂等、断点续传）。

### M4 回测（任务化）
- `backtests/service.create()`：校验配额（并发/区间/标的）→ 落 `backtests(queued)` → `backtest_tasks.run_backtest.delay(id)` → 返回 id+job_id。
- `backtest_tasks.run_backtest()`：加载策略版本 + 构建 DataFeed（PIT）→ 调 `IBacktestEngine.run()`（backtrader）→ 流式写 equity/trades/positions → 计算 metrics → 更新状态/进度（Redis + DB）。
- 取消：检查 `cancel_flag`（Redis），引擎周期性检查并优雅退出。

### M5 报告
- `reports/service.py`：用 `quantstats`/`empyrical` 由 equity/trades 计算并渲染 HTML，PDF 经 weasyprint/playwright 导出；分享链接签名 token + 有效期。

### M6 因子（任务化）
- `factors/service.py`：`compute`（按日批量算因子值，写 `factor_values`）、`analyze`（IC/分层，写 `factor_analyses`）、`combine`（去极值/中性化/加权）。

### M7 组合 / M8 交易
- `portfolios/service.rebalance()`：取目标权重 → 与当前持仓 diff → 生成订单（取整/阈值）→ 过风控（M9）→ 提交执行引擎（Paper/券商）。
- `trading`：订单状态机推进；PaperGateway 用 DataFeed 行情按规则撮合；实盘经 vnpy 网关（自托管）回报。
- 调度：`beat` 在交易日盘后触发组合再平衡（按 `rebalance` 频率）。

### M9 风控
- `engine/risk`：`RiskEngine.check(order, context) -> Decision`；规则可组合；回测/仿真/实盘共用同一引擎；触发写 `risk_events` + 告警。

### M10 告警监控
- `core/alerting`：渠道适配器（email/webhook/钉钉/飞书/serverchan），去重（dedup_key）+ 限频；`alerts` 落库后异步投递。
- 监控：prometheus 指标（http/任务/队列/引擎耗时）；`/healthz` 检查 DB/Redis/上游。

---

## 6. TDD 驱动测试

### 6.1 流程与组织

- **测试先行**：先写失败用例再实现（`AGENTS.md` 要求）。
- 目录：`tests/unit`（service/engine 纯逻辑）、`tests/integration`（API + DB）、`tests/engine`（回测/因子口径用例）。
- 夹具：pytest fixtures 提供测试 DB（事务回滚）、伪 DataFeed（确定性行情）、伪 Gateway。

### 6.2 测试矩阵（按模块）

| 模块 | 关键用例 |
|------|---------|
| M1 | 注册唯一性、登录限速、JWT 过期/刷新、API Key 一次性与越 scope、租户越权 403 |
| M2 | HMAC 签名正确性、同步幂等、文件导入与 API 一致、PIT 无未来、缺口探测 |
| M3 | 配置式 schema 校验、代码式沙箱拦截（联网/文件）、版本可复现 |
| M4 | T+1 不可当日卖、涨停不可买/跌停不可卖、停牌跳过、成本模型、确定性复现、取消 |
| M5 | 夏普/最大回撤/卡玛口径、基准对齐、报告生成 |
| M6 | 因子 PIT、RankIC、分层单调性、中性化后暴露下降 |
| M7 | 再平衡取整/阈值、T+1 可用量、账实一致 |
| M8 | 订单状态机、Paper 撮合=回测口径、风控拦截、实盘网关 mock 回报 |
| M9 | 各规则触发与动作（拒单/告警/强平）、回撤熔断阈值 |
| M10 | 告警去重限频、审计落库、健康检查 |

### 6.3 引擎口径用例模板

```python
def test_t_plus_1_blocks_same_day_sell(fake_feed, engine):
    # 给定 D 日买入
    # 当 D 日尝试卖出
    # 则被拒（T+1），D+1 可卖
    ...

def test_limit_up_blocks_buy(fake_feed, engine):
    # 涨停标记为 True 的 bar 不应产生买入成交
    ...
```

### 6.4 覆盖率

- 核心引擎（backtest/factor/risk/execution）行覆盖 ≥ 85%；service 层 ≥ 75%。

---

## 7. 基础设施与部署

### 7.1 运行模式

- **本地开发**：Postgres/Redis 用 Docker 起，api/worker/beat 本地直跑（热重载）。
- **线上**：docker-compose 编排 `postgres / redis / api / worker-* / beat / frontend`。

### 7.2 本地开发

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env                 # 配置 DB/Redis/JWT/数据源凭证
docker compose -f deploy/docker-compose.dev.yml up -d postgres redis
alembic upgrade head
uvicorn app.main:app --reload --port 8000        # api
celery -A app.tasks.celery_app worker -Q backtest,factor,data,trade -l info   # worker
celery -A app.tasks.celery_app beat -l info                                   # beat
pytest -q
```

### 7.3 环境变量（`backend/.env`）

```bash
APP_ENV=dev
API_PORT=8000
# 安全
JWT_SECRET=...
JWT_ACCESS_TTL=1800
JWT_REFRESH_TTL=604800
CONFIG_ENC_KEY=...           # 加密 data 服务 secretKey
# PostgreSQL（宿主端口错开 warden-stock-data 的 5432/6379；Docker 部署时 PG_HOST/PG_PORT 由 compose 覆盖为 postgres:5432）
PG_HOST=localhost
PG_PORT=5433
PG_USER=warden
PG_PASSWORD=...
PG_DB=warden_quant
# Redis（宿主端口错开为 6380；容器内部仍为 6379）
REDIS_HOST=localhost
REDIS_PORT=6380
# Celery
CELERY_BROKER_URL=redis://localhost:6380/1
CELERY_RESULT_BACKEND=redis://localhost:6380/2
# warden-stock-data 数据源（亦可走 DB 凭证表，优先 DB）
DATA_BASE_URL=http://localhost:8080
DATA_SECRET_ID=...
DATA_SECRET_KEY=...
# 回测/任务配额默认（可被 plan 覆盖）
MAX_CONCURRENT_BACKTESTS=2
MAX_UNIVERSE=500
MAX_RANGE_DAYS=2520
# 实盘（默认关闭；自托管启用）
LIVE_ENABLED=false
```

### 7.4 docker-compose 服务（线上）

遵循 `AGENTS.md` 部署规范：顶层 `name: warden-stock-quant`，自建镜像 `image: warden-stock-quant-<service>`，PostgreSQL 数据 bind mount 到 `backend/deploy/pgdata`（入 `.gitignore`）。

```yaml
name: warden-stock-quant
services:
  postgres:
    image: postgres:16
    volumes: ["./pgdata:/var/lib/postgresql/data"]    # bind mount 到项目内
    environment: [POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB]
  redis:
    image: redis:7
  api:
    image: warden-stock-quant-api
    build: { context: .., dockerfile: deploy/Dockerfile }
    command: gunicorn -k uvicorn.workers.UvicornWorker app.main:app -b 0.0.0.0:8000
    depends_on: [postgres, redis]
    ports: ["8000:8000"]
  worker:
    image: warden-stock-quant-worker
    build: { context: .., dockerfile: deploy/Dockerfile }
    command: celery -A app.tasks.celery_app worker -Q backtest,factor,data,trade -l info
    depends_on: [postgres, redis]
  beat:
    image: warden-stock-quant-beat
    build: { context: .., dockerfile: deploy/Dockerfile }
    command: celery -A app.tasks.celery_app beat -l info
    depends_on: [redis]
  frontend:
    image: warden-stock-quant-frontend
    build: { context: ../../frontend }
    ports: ["80:80"]
```

> 实盘 worker（券商网关）仅在自托管合规环境单独编排，不随公网部署启用。

### 7.5 中间件装配顺序

`api`（FastAPI）中间件由外到内：`RequestID/Trace` → `CORS` → `Logging` → `RateLimit` → `Auth(JWT/APIKey)` → `TenantScope` → 路由 → `Audit`（写操作）。所有路由支持超时（asyncio timeout）与取消传播。

---

## 8. 并行开发约定（后端视角）

1. **契约先行**：以 `openapi.yaml` 为唯一契约；前后端按它并行；变更先改契约再实现。
2. **统一响应/错误码**：见 §1.5，前端据此处理。
3. **异步资源协议**：提交→轮询（`job_id` + 状态/进度），前端用轮询/订阅。
4. **decimal 字符串**：金额/比率对外为字符串，前端转 number 前置。
5. **租户隔离**：所有业务接口默认当前用户作用域，前端无需传 user_id。
6. **文档同步**：核心功能变更同步 `PRD.md`/`BACKEND.md`/相关引擎文档/`openapi.yaml`（`AGENTS.md` 要求）。

---

> 本文档与 `QUANT_ENGINE.md` / `DATA_ACCESS.md` 互补；接口以 `openapi.yaml` 为权威。
