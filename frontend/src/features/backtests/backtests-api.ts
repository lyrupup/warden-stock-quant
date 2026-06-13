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
  TReportAnalysis,
  TCompareRow,
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

  analysis: (id: number) =>
    unwrap<TReportAnalysis>(api.get(`backtests/${id}/analysis`)),

  /** 下载 HTML 绩效报告 */
  downloadReportHtml: async (id: number) => {
    const res = await api.get(`backtests/${id}/report`, {
      searchParams: { format: "html" },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `backtest-report-${id}.html`;
    a.click();
    URL.revokeObjectURL(url);
  },

  downloadReportPdf: async (id: number) => {
    const res = await api.get(`backtests/${id}/report`, {
      searchParams: { format: "pdf" },
    });
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `backtest-report-${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  },

  createShareLink: (id: number, expiresIn = 86400) =>
    unwrap<{ url: string; token: string; expires_at: string }>(
      api.post(`backtests/${id}/share`, { json: { expires_in: expiresIn } }),
    ),

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

export const reportsApi = {
  compare: (backtestIds: number[]) =>
    unwrap<{ rows: TCompareRow[] }>(
      api.post("reports/compare", { json: { backtest_ids: backtestIds } }),
    ),
};
