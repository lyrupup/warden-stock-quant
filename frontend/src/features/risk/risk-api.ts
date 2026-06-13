import { api, unwrap } from "@/core/http";
import type { TPageData } from "@/types";

export type TRiskRule = {
  type: string;
  params?: Record<string, unknown>;
  action: string;
  enabled: boolean;
};

export type TRiskRuleSet = {
  id: number;
  name: string;
  scope: string;
  is_platform: boolean;
  rules: TRiskRule[];
  created_at: string;
};

export type TRiskEvent = {
  id: number;
  portfolio_id?: number;
  order_id?: number;
  rule_type: string;
  action: string;
  detail?: { reason?: string };
  created_at: string;
};

export const riskApi = {
  listRuleSets: (page = 1, size = 20) =>
    unwrap<TPageData<TRiskRuleSet>>(api.get("risk/rule-sets", { searchParams: { page, size } })),

  createRuleSet: (payload: { name: string; scope?: string; rules: TRiskRule[] }) =>
    unwrap<TRiskRuleSet>(api.post("risk/rule-sets", { json: payload })),

  updateRuleSet: (id: number, payload: { name: string; scope?: string; rules: TRiskRule[] }) =>
    unwrap<TRiskRuleSet>(api.put(`risk/rule-sets/${id}`, { json: payload })),

  deleteRuleSet: (id: number) => unwrap<null>(api.delete(`risk/rule-sets/${id}`)),

  listEvents: (page = 1, size = 20, portfolioId?: number) =>
    unwrap<TPageData<TRiskEvent>>(
      api.get("risk/events", {
        searchParams: {
          page,
          size,
          ...(portfolioId != null ? { portfolio_id: portfolioId } : {}),
        },
      }),
    ),
};
