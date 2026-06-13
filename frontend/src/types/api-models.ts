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
