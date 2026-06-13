import { api, unwrap } from "@/core/http";
import type { TPageData } from "@/types";

export type TPortfolio = {
  id: number;
  name: string;
  mode: string;
  strategy_version_id?: number;
  init_capital: string;
  cash: string;
  benchmark: string;
  rebalance: string;
  status: string;
  created_at: string;
};

export type TPosition = {
  id: number;
  code: string;
  qty: number;
  avail_qty: number;
  market_value?: string;
  pnl?: string;
};

export const portfoliosApi = {
  list: (page = 1, size = 20) =>
    unwrap<TPageData<TPortfolio>>(api.get("portfolios", { searchParams: { page, size } })),

  get: (id: number) => unwrap<TPortfolio>(api.get(`portfolios/${id}`)),

  create: (payload: Record<string, unknown>) =>
    unwrap<TPortfolio>(api.post("portfolios", { json: payload })),

  delete: (id: number) => unwrap<null>(api.delete(`portfolios/${id}`)),

  positions: (id: number) => unwrap<TPosition[]>(api.get(`portfolios/${id}/positions`)),

  rebalance: (id: number) =>
    unwrap<{ trade_date: string; targets: unknown[]; message: string }>(
      api.post(`portfolios/${id}/rebalance`),
    ),
};
