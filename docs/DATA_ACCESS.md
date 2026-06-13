# 守望者量化交易系统 · 行情数据接入与数据集文档

> Warden Stock Quant · Data Access & Dataset（消费 warden-stock-data）
>
> 前置阅读：[`PRD.md`](./PRD.md) · [`BACKEND.md`](./BACKEND.md) · [`QUANT_ENGINE.md`](./QUANT_ENGINE.md)
>
> 上游数据契约：`warden-stock-data` 的 [`API_GUIDE.md`](../../warden-stock-data/docs/API_GUIDE.md) 与 `openapi.yaml`（以其为权威）。本项目是其**只读消费方**。

---

## 1. 数据来源与边界

本项目**不生产行情数据**，全部来自 `warden-stock-data`：

| 来源 | 用途 | 说明 |
|------|------|------|
| **开放 API** `/open/v1/*`（HMAC 签名）| 增量同步 / 在线查询 | 指数、快照、K 线、分时、指标、搜索、证券列表、元数据 |
| **全市场 K 线导出文件**（CSV/Parquet）| 首次全量灌库最快路径 | 批量导入历史日 K，再用 API 增量追平 |

**铁律**：本项目对上游**零写权限**；凭证由平台集中托管，用户不接触（PRD §3.2）。

---

## 2. HMAC 数据客户端

### 2.1 签名规则（对齐上游 API_GUIDE §3）

每个请求带 4 个头：`X-Secret-Id` / `X-Timestamp`（unix 毫秒）/ `X-Nonce`（一次性）/ `X-Signature`。

```
StringToSign = METHOD\nPATH\nCanonicalQuery\nX-Secret-Id\nX-Timestamp\nX-Nonce\nSHA256Hex(Body)
Signature    = Base64( HMAC_SHA256(secretKey, StringToSign) )
CanonicalQuery: query 参数按 key 字典序升序，key=value 用 & 连接；无参数为空串
```

时间戳偏差需在 ±300s 内，nonce 300s 窗口内不可重复。

### 2.2 Python 客户端实现

```python
# app/core/data/client/warden_data.py
import time, uuid, hashlib, hmac, base64, httpx

class WardenDataClient:
    def __init__(self, base_url, secret_id, secret_key, timeout=10):
        self._base = base_url.rstrip("/")
        self._sid, self._skey = secret_id, secret_key
        self._http = httpx.Client(timeout=timeout)

    def _headers(self, method, path, query: dict, body: str = ""):
        ts = str(int(time.time() * 1000))
        nonce = uuid.uuid4().hex
        cq = "&".join(f"{k}={query[k]}" for k in sorted(query)) if query else ""
        body_hash = hashlib.sha256(body.encode()).hexdigest()
        sts = "\n".join([method, path, cq, self._sid, ts, nonce, body_hash])
        sig = base64.b64encode(
            hmac.new(self._skey.encode(), sts.encode(), hashlib.sha256).digest()
        ).decode()
        return {"X-Secret-Id": self._sid, "X-Timestamp": ts,
                "X-Nonce": nonce, "X-Signature": sig}

    def get(self, path: str, query: dict | None = None) -> dict:
        query = query or {}
        r = self._http.get(self._base + path, params=query,
                            headers=self._headers("GET", path, query))
        r.raise_for_status()
        body = r.json()
        if body.get("code") != 0:
            raise WardenDataError(body["code"], body.get("message"))
        return body["data"]
```

### 2.3 封装的上游接口

| 方法 | 上游路径 | 用途 |
|------|---------|------|
| `indices()` | `/open/v1/indices` | 大盘指数（基准）|
| `quotes(codes)` | `/open/v1/quotes` | 批量快照 |
| `kline(code, period, adjust, from, to)` | `/open/v1/stocks/{code}/kline` | 日 K（回测/同步主力）|
| `intraday(code)` | `/open/v1/stocks/{code}/intraday` | 分时（研判，可选）|
| `indicators_batch(codes, types, trade_date)` | `/open/v1/indicators` | **PIT 指标快照（回测/因子关键）** |
| `indicators_one(code, types)` | `/open/v1/stocks/{code}/indicators` | 单只实时指标（非快照指标补齐）|
| `search(kw)` | `/open/v1/search` | 搜索 |
| `securities()` | `/open/v1/securities` | 证券列表 |
| `meta()` | `/open/v1/meta` | 能力发现（指标目录 / `default_snapshot_types` / freshness）|

### 2.4 容错与降级

- **重试退避**：网络/5xx/`52001` 指数退避重试（上限 N 次）；`429`（上游限流/配额）退避更久。
- **stale 标记**：上游降级返回 `stale=true` 时记录并按业务决定是否采用。
- **平台侧限流**：在本平台对上游调用做集中限流，避免触发上游 `42001/42002`。
- **能力发现先行**：同步前先调 `meta()` 确认 `default_snapshot_types`，决定哪些指标可批量按日 PIT 读取，其余经单只接口或本地重算。

---

## 3. 本地数据集（market schema）

为支撑大规模回测/因子计算的高性能、可重复读取，落地本地数据集（避免每次回测打满上游）。

### 3.1 表结构

```sql
CREATE SCHEMA IF NOT EXISTS market;

-- 证券元数据
CREATE TABLE market.securities (
  code VARCHAR(16) PRIMARY KEY,         -- 600000
  name VARCHAR(64), market VARCHAR(8) DEFAULT 'CN',
  board VARCHAR(32),                    -- 主板/创业板/科创板...
  list_date DATE, delist_date DATE,
  is_st BOOLEAN DEFAULT false, status VARCHAR(16) DEFAULT 'listed',
  updated_at TIMESTAMPTZ DEFAULT now()
);

-- 交易日历
CREATE TABLE market.trading_calendar (
  trade_date DATE PRIMARY KEY, is_open BOOLEAN NOT NULL
);

-- 日 K（核心大表，按年分区）
CREATE TABLE market.daily_bars (
  code VARCHAR(16) NOT NULL,
  trade_date DATE NOT NULL,
  open NUMERIC(20,4), high NUMERIC(20,4), low NUMERIC(20,4), close NUMERIC(20,4),
  volume NUMERIC(24,4), amount NUMERIC(24,4),
  adj_factor NUMERIC(20,8) DEFAULT 1,    -- 复权因子
  limit_up NUMERIC(20,4), limit_down NUMERIC(20,4),
  suspended BOOLEAN DEFAULT false, is_st BOOLEAN DEFAULT false,
  PRIMARY KEY (code, trade_date)
) PARTITION BY RANGE (trade_date);
CREATE INDEX idx_bars_date ON market.daily_bars(trade_date);

-- PIT 指标快照（盘后全市场，回测/因子按日读取）
CREATE TABLE market.indicator_snapshots (
  code VARCHAR(16) NOT NULL, trade_date DATE NOT NULL,
  type VARCHAR(32) NOT NULL, value NUMERIC(20,8),
  PRIMARY KEY (code, trade_date, type)
) PARTITION BY RANGE (trade_date);

-- 同步作业
CREATE TABLE market.data_sync_jobs (
  id BIGSERIAL PRIMARY KEY,
  type VARCHAR(32),                      -- securities|daily_bars|indicators|calendar|import_file
  scope JSONB,                           -- 全量/指定代码/区间
  status VARCHAR(16) DEFAULT 'queued',   -- queued|running|succeeded|failed
  progress NUMERIC(5,2) DEFAULT 0,
  total INT, done INT, failed INT,
  detail JSONB, error TEXT,
  started_at TIMESTAMPTZ, finished_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

> 复权口径：库内存**不复权原始 OHLC + adj_factor**，回测/因子按需算 qfq/hfq，保证口径灵活且一致；或额外缓存 qfq 列加速默认路径。

### 3.2 列存加速（已确认引入）

大规模因子计算（全市场×多年）下 PostgreSQL 行存会成为瓶颈，**本项目确认引入 Parquet + DuckDB 列存加速层**：

- 把 `daily_bars`（及指标快照、因子值）镜像为按 `(year)` / 可选 `(code 前缀)` 分区的 **Parquet**，落 `data/parquet/`（入 `.gitignore`）。
- 用 **DuckDB / pyarrow** 做列式批量读取与截面计算（因子计算、回测预读区间走列存）。
- **PostgreSQL 仍为权威源**，Parquet 为**只读派生加速层**，由同步任务在日 K/指标更新后幂等重建对应分区；DataFeed 优先读 Parquet，缺失回退 PostgreSQL。
- `core/data/feed` 提供 `ParquetFeed` 与 `PgFeed` 两实现，经配置 `DATA_FEED_BACKEND=parquet|pg|auto` 选择（默认 `auto`：批量截面走 parquet，点查走 pg）。

### 3.3 上游待补能力（指数成分 / 行业 / 市值）

`warden-stock-data` **暂未提供**以下开放接口，后续会支持。本项目**先预留接口与字段、能力先留空/降级**：

| 能力 | 依赖上游接口 | 当前处理 |
|------|------------|---------|
| 股票池按**指数成分**选股（`universe.type=index`）| 指数成分股名单 API | 接口占位，调用返回 `not_implemented`；前端禁用该选项并提示「待上游支持」|
| 因子**行业中性化** | 细分行业分类（如申万）API | 中性化选项 `industry` 占位；暂用 `securities.board`（板块）做粗粒度近似，或缺省关闭 |
| 因子**市值中性化** | 总市值 / 流通市值字段 | 中性化选项 `market_cap` 占位，缺省关闭 |

> 上游接口就绪后，仅需在 `WardenDataClient` 增加对应方法 + 同步任务写入新表（如 `market.index_constituents` / `securities.industry` / `daily_bars.market_cap`），上层 DataFeed 与因子中性化即可启用，无需改动 API 契约。

---

## 4. 同步策略

### 4.1 三类同步作业

| 作业 | 触发 | 逻辑 |
|------|------|------|
| **证券/日历同步** | 每日盘前（如 8:30）| `securities()` + 交易日历更新 securities / trading_calendar |
| **增量日 K 同步** | 每日盘后（如 17:00，交易日）| 对全市场逐代码取 `kline(from=上次同步日+1)`，分批+并发，幂等 upsert |
| **PIT 指标同步** | 盘后日 K 之后 | `indicators_batch(codes, default_snapshot_types, trade_date)` 落 indicator_snapshots |

- **首次全量**：优先用**冷备文件直导**（§5）灌历史日 K，再用增量 API 追平最近缺口。
- 调度由 Celery beat 触发（交易日历感知，仅交易日运行），分批/并发受配额与上游限流约束。

### 4.2 幂等与断点续传

- 所有写为 `INSERT ... ON CONFLICT DO UPDATE`（upsert）。
- 作业记录 `done/failed` 与失败代码列表，可只重试失败项。
- 缺口探测：对比 `trading_calendar` 与各代码 `max(trade_date)`，自动补缺。

### 4.3 同步任务示例

```python
# app/tasks/data_tasks.py
@celery.task(bind=True)
def sync_daily_bars(self, codes=None, date_from=None):
    client = build_data_client()           # 从 data_source_credentials 解密构建
    cal = client_calendar_gap()            # 交易日历缺口
    codes = codes or list_all_codes()
    for batch in chunked(codes, size=20):  # 分批
        for code in batch:
            data = client.kline(code, period="day", adjust="",
                                 from_=date_from or last_date(code))
            upsert_daily_bars(code, data)   # 幂等
        update_job_progress(self.request.id)
```

---

## 5. 冷备文件直导（首次全量推荐）

`warden-stock-data` 在 `backend/data-export/` 维护**全市场历史行情冷备**（gzip CSV，约 1680 万行日 K + 证券 + 交易日历 + 复权因子）。逐只股票走 HMAC API 全量回补耗时数小时，**首次构建数据集 / 大规模回补优先用冷备直导**：读 gz CSV 用 PostgreSQL `COPY` 灌库，5–15 分钟完成。

实现：`backend/app/cli/import_backup.py`（asyncpg `copy_records_to_table` 流式导入）+ `backend/deploy/import-data.sh`（一键脚本，容器内执行、只读挂载冷备目录、内网直连 postgres）。

字段映射（冷备列 → 本地 market 表）：

| 冷备文件 | 目标表 | 关键映射 |
|----------|--------|----------|
| `securities.csv.gz` | `market_securities` | `status` 1→`listed`/0→`delisted`；`is_st` `t/f`→bool |
| `trading_calendars.csv.gz` | `market_trading_calendar` | 仅取 `market=CN`，`cal_date`→`trade_date` |
| `stock_daily_klines.csv.gz` | `market_daily_bars` | `stock_code`→`code`；`trade_status` 0→`suspended=true`；价格为前复权（qfq），`adj_factor=1`；丢弃 `pre_close/turnover_rate/pct_chg/source/adjust` |

> 注：冷备日 K 为**前复权（qfq）**价，导入后 `adj_factor` 统一置 1；若回测需不复权口径，后续可结合 `stock_adjust_factors` 自行还原。

操作步骤：

```bash
# 1) 启动本地 Docker 栈（postgres/redis/api/worker/beat）
cd backend/deploy && docker compose up -d

# 2) 一键导入冷备（默认指向同级 warden-stock-data/backend/data-export）
./import-data.sh
# 指定目录 / 仅导某表 / 不清空旧数据：
./import-data.sh /path/to/data-export -- --only bars --no-truncate
```

- 默认 `--truncate`：导入前清空目标表后全量灌入（首次/重灌最快）；增量合并用 `--no-truncate`。
- 幂等：按主键 `(code, trade_date)` 去重，可重复导入。
- 导入完成后，再用**增量 API 同步**（§4）从冷备截止日追平至最新交易日。

---

## 6. 数据质量与新鲜度

- `GET /api/v1/datasets/status` 暴露：最新交易日、各表更新至、证券数、缺口列表、上游 `freshness`、`stale` 提示。
- 质量校验：价格非负、`low<=open/close<=high`、复权因子单调性、停牌日无异常成交量；异常入质量报告并告警（M10）。
- **PIT 保证**：回测/因子取数只用 `trade_date <= as_of` 的记录；指标优先用上游 PIT 快照，缺口用本地一致重算（口径对齐 QUANT_ENGINE §5/§7）。

---

## 7. 与引擎的衔接

- `DataFeed`（QUANT_ENGINE §3）的所有方法最终读 `market` schema（或 Parquet 派生层），不直接打上游 API（仿真盘后取最新数据除外）。
- 回测区间数据预读入内存 → 构造 backtrader feed；因子计算按日截面批量读。
- 基准指数（如 000300）经 `indices()`/本地指数表提供给绩效对比。

---

> 上游契约以 `warden-stock-data` 的 `openapi.yaml` 为权威；本项目随上游升级需回归同步与导入用例。
