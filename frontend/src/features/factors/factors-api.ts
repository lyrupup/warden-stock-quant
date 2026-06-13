import { api, unwrap } from "@/core/http";
import type { TPageData } from "@/types";

export type TFactor = {
  id?: number;
  name: string;
  category?: string;
  type: string;
  expr?: string;
  direction?: number;
  created_at?: string;
};

export type TFactorAnalysis = {
  id: number;
  status: string;
  ic_mean?: string;
  ic_ir?: string;
  ic_win_rate?: string;
  ic_series?: { trade_date: string; ic: number }[];
  quantile_returns?: Record<string, number>;
};

export const factorsApi = {
  list: (page = 1, size = 20) =>
    unwrap<TPageData<TFactor>>(api.get("factors", { searchParams: { page, size } })),

  create: (payload: Partial<TFactor>) => unwrap<TFactor>(api.post("factors", { json: payload })),

  delete: (id: number) => unwrap<null>(api.delete(`factors/${id}`)),

  compute: (id: number, body: Record<string, unknown>) =>
    unwrap<{ id: number; job_id: string }>(api.post(`factors/${id}/compute`, { json: body })),

  analyze: (id: number, body: Record<string, unknown>) =>
    unwrap<{ id: number; job_id: string }>(api.post(`factors/${id}/analyze`, { json: body })),

  getAnalysis: (factorId: number, analysisId: number) =>
    unwrap<TFactorAnalysis>(api.get(`factors/${factorId}/analyses/${analysisId}`)),
};
