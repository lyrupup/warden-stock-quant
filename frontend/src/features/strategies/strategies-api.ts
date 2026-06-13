import { api, unwrap } from "@/core/http";
import type {
  TPageData,
  TStrategy,
  TStrategyTemplate,
  TStrategyValidateResult,
  TStrategyVersion,
  TUniverse,
} from "@/types";

export type TStrategyUpsert = {
  name: string;
  type: "config" | "code";
  description?: string;
  config?: Record<string, unknown>;
  params_schema?: Record<string, unknown>;
  default_params?: Record<string, unknown>;
  universe?: TUniverse;
};

export const strategiesApi = {
  list: (page = 1, size = 20) =>
    unwrap<TPageData<TStrategy>>(api.get("strategies", { searchParams: { page, size } })),

  get: (id: number) => unwrap<TStrategy>(api.get(`strategies/${id}`)),

  create: (payload: TStrategyUpsert) =>
    unwrap<TStrategy>(api.post("strategies", { json: payload })),

  update: (id: number, payload: TStrategyUpsert) =>
    unwrap<TStrategy>(api.put(`strategies/${id}`, { json: payload })),

  remove: (id: number) => unwrap<null>(api.delete(`strategies/${id}`)),

  versions: (id: number) =>
    unwrap<TStrategyVersion[]>(api.get(`strategies/${id}/versions`)),

  validate: (id: number, payload?: Partial<TStrategyUpsert>) =>
    unwrap<TStrategyValidateResult>(
      api.post(`strategies/${id}/validate`, { json: payload ?? {} }),
    ),

  templates: () => unwrap<TStrategyTemplate[]>(api.get("strategy-templates")),
};
