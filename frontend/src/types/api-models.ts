/**
 * 与 docs/openapi.yaml 对齐的核心领域类型（手写，T/E 前缀）。
 * 说明：本骨架阶段采用「手写核心类型」方式（见 types/README）。
 * 也提供 `pnpm gen:api` 由 openapi.yaml 生成 `types/api.d.ts` 作为补充校对来源。
 */

/** 后端 decimal 高精度数值统一以字符串传输 */
export type TDecimal = string;

/** 用户角色 */
export enum ERole {
  User = "user",
  Admin = "admin",
}

/** 异步任务状态机 */
export enum EJobStatus {
  Queued = "queued",
  Running = "running",
  Succeeded = "succeeded",
  Failed = "failed",
  Canceled = "canceled",
}

/** API Key 作用域 */
export enum EApiKeyScope {
  Read = "read",
  Backtest = "backtest",
  Factor = "factor",
  Trade = "trade",
}

/** 统一响应包络 { code, message, data } */
export type TApiResponse<T = unknown> = {
  code: number;
  message: string;
  data: T;
};

/** 统一分页结构 { list, total, page, size } */
export type TPageData<T> = {
  list: T[];
  total: number;
  page: number;
  size: number;
};

/** /auth/* 返回的令牌数据（data 部分） */
export type TTokenResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

/** /me 当前用户信息与配额 */
export type TMe = {
  id: number;
  email: string;
  username?: string;
  role: ERole;
  plan?: string;
  live_enabled?: boolean;
  quota?: Record<string, unknown>;
};

/** API Key 列表项 */
export type TApiKey = {
  id: number;
  name: string;
  prefix?: string;
  scopes: EApiKeyScope[] | string[];
  status?: string;
  created_at?: string;
  last_used_at?: string | null;
};

/** 创建 API Key 后一次性返回的明文 */
export type TApiKeyCreated = {
  id: number;
  key: string;
};

/** 异步任务 */
export type TJob = {
  id: string;
  type: string;
  ref_id?: number;
  status: EJobStatus;
  progress?: TDecimal;
  result?: Record<string, unknown>;
  error?: string;
  created_at?: string;
};

/** M2 数据集状态 */
export type TDatasetStatus = {
  latest_trade_date?: string | null;
  bars_updated_to?: string | null;
  securities_count: number;
  gaps: string[];
  stale: boolean;
};

/** 数据源凭证（管理员） */
export type TDataSource = {
  id: number;
  name?: string;
  base_url: string;
  secret_id: string;
  qps_limit?: number;
  daily_quota?: number;
  enabled: boolean;
};

/** 股票池定义 */
export type TUniverse = {
  type: "all" | "index" | "list" | "factor";
  code?: string;
  codes?: string[];
  filter?: Record<string, unknown>;
};

/** 配置式策略 JSON */
export type TStrategyConfig = {
  signals: Array<Record<string, unknown>>;
  rebalance?: { freq?: "day" | "week" | "month" };
  position?: {
    scheme?: string;
    max_n?: number;
    scale_in?: Record<string, unknown>;
  };
  stop?: { stop_loss?: number; take_profit?: number; trailing?: number; observe_stop_loss?: number };
};

/** 策略 */
export type TStrategy = {
  id: number;
  name: string;
  type: "config" | "code";
  description?: string;
  latest_version: number;
  config?: TStrategyConfig;
  code?: string;
  params_schema?: Record<string, unknown>;
  default_params?: Record<string, unknown>;
  universe?: TUniverse;
  created_at?: string;
  updated_at?: string;
};

/** 策略版本 */
export type TStrategyVersion = {
  id: number;
  strategy_id: number;
  version: number;
  config?: TStrategyConfig;
  params_schema?: Record<string, unknown>;
  default_params?: Record<string, unknown>;
  universe?: TUniverse;
  created_at?: string;
};

/** 策略模板 */
export type TStrategyTemplate = {
  id: string;
  name: string;
  description: string;
  type: "config" | "code";
  config: TStrategyConfig;
  params_schema: Record<string, unknown>;
  default_params: Record<string, unknown>;
  universe: TUniverse;
};

/** 策略校验结果 */
export type TStrategyValidateResult = {
  valid: boolean;
  errors: string[];
};

/** 回测状态机 */
export type TBacktestStatus = "queued" | "running" | "succeeded" | "failed" | "canceled";

/** 成本配置 */
export type TCostConfig = {
  commission_rate?: number;
  commission_min?: number;
  stamp_tax_rate?: number;
  slippage_type?: "none" | "pct" | "tick" | "volume";
  slippage_value?: number;
};

/** 创建回测请求 */
export type TBacktestCreate = {
  name?: string;
  strategy_version_id: number;
  params?: Record<string, unknown>;
  universe?: TUniverse;
  date_from: string;
  date_to: string;
  init_capital: number;
  benchmark?: string;
  adjust?: string;
  cost_config?: TCostConfig;
};

/** 回测 */
export type TBacktest = {
  id: number;
  name?: string;
  status: TBacktestStatus;
  progress: string | number;
  job_id?: string;
  strategy_version_id: number;
  strategy_id?: number | null;
  strategy_name?: string | null;
  strategy_version?: number | null;
  date_from: string;
  date_to: string;
  init_capital: string | number;
  benchmark: string;
  adjust: string;
  error?: string;
  created_at?: string;
  finished_at?: string;
};

/** 回测绑定的策略版本快照 */
export type TBacktestStrategy = {
  strategy_version_id: number;
  strategy_id?: number | null;
  strategy_name?: string | null;
  version?: number | null;
  type?: "config" | "code" | null;
  description?: string | null;
  config?: TStrategyConfig;
  universe?: TUniverse;
  params?: Record<string, unknown>;
  created_at?: string | null;
};

/** 回测绩效指标 */
export type TBacktestMetrics = {
  total_return?: string | number;
  annual_return?: string | number;
  volatility?: string | number;
  sharpe?: string | number;
  sortino?: string | number;
  calmar?: string | number;
  max_drawdown?: string | number;
  mdd_from?: string;
  mdd_to?: string;
  win_rate?: string | number;
  profit_factor?: string | number;
  turnover?: string | number;
  alpha?: string | number;
  beta?: string | number;
  info_ratio?: string | number;
};

/** 净值点 */
export type TEquityPoint = {
  trade_date: string;
  nav?: string | number;
  benchmark_nav?: string | number;
  drawdown?: string | number;
};

/** 回测成交 */
export type TBacktestTrade = {
  id: number;
  trade_date: string;
  code: string;
  side: "buy" | "sell";
  price?: string | number;
  qty: number;
  amount?: string | number;
  commission?: string | number;
  tax?: string | number;
  pnl?: string | number;
};

/** 回测持仓 */
export type TBacktestPosition = {
  trade_date: string;
  code: string;
  qty: number;
  price?: string | number;
  market_value?: string | number;
  weight?: string | number;
};

/** 异步任务受理返回 */
export type TJobAccepted = {
  id: number;
  job_id: string;
};
