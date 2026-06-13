import { api, unwrap } from "@/core/http";
import type {
  TBacktest,
  TBacktestCreate,
  TBacktestMetrics,
  TBacktestPosition,
  TBacktestStrategy,
  TBacktestTrade,
  TEquityPoint,
  TJobAccepted,
  TOptimization,
  TOptimizationCreate,
  TOptimizationResult,
  TPageData,
} from "@/types";

export const backtestsApi = {
  list: (page = 1, size = 20) =>
    unwrap<TPageData<TBacktest>>(api.get("backtests", { searchParams: { page, size } })),

  get: (id: number) => unwrap<TBacktest>(api.get(`backtests/${id}`)),

  strategy: (id: number) =>
    unwrap<TBacktestStrategy>(api.get(`backtests/${id}/strategy`)),

  create: (payload: TBacktestCreate) =>
    unwrap<TJobAccepted>(api.post("backtests", { json: payload })),

  cancel: (id: number) => unwrap<null>(api.post(`backtests/${id}/cancel`)),

  metrics: (id: number) => unwrap<TBacktestMetrics>(api.get(`backtests/${id}/metrics`)),

  equity: (id: number) => unwrap<TEquityPoint[]>(api.get(`backtests/${id}/equity`)),

  trades: (id: number, page = 1, size = 50) =>
    unwrap<TPageData<TBacktestTrade>>(
      api.get(`backtests/${id}/trades`, { searchParams: { page, size } }),
    ),

  positions: (id: number, date?: string) =>
    unwrap<TBacktestPosition[]>(
      api.get(`backtests/${id}/positions`, {
        searchParams: date ? { date } : {},
      }),
    ),
};

export const optimizationsApi = {
  list: (page = 1, size = 20) =>
    unwrap<TPageData<TOptimization>>(
      api.get("optimizations", { searchParams: { page, size } }),
    ),

  get: (id: number) => unwrap<TOptimization>(api.get(`optimizations/${id}`)),

  results: (id: number) =>
    unwrap<TOptimizationResult[]>(api.get(`optimizations/${id}/results`)),

  create: (payload: TOptimizationCreate) =>
    unwrap<TJobAccepted>(api.post("optimizations", { json: payload })),

  cancel: (id: number) => unwrap<null>(api.post(`optimizations/${id}/cancel`)),
};
