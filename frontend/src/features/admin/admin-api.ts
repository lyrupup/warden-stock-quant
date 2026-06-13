import { api, unwrap } from "@/core/http";
import type { TDataSource } from "@/types";

export type TDataSourceCreate = {
  name?: string;
  base_url: string;
  secret_id: string;
  secret_key: string;
  qps_limit?: number;
  daily_quota?: number;
};

export const adminApi = {
  listDataSources: () => unwrap<TDataSource[]>(api.get("admin/data-source")),

  createDataSource: (payload: TDataSourceCreate) =>
    unwrap<TDataSource>(api.post("admin/data-source", { json: payload })),
};
