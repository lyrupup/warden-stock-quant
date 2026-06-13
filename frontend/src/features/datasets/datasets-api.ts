import { api, unwrap } from "@/core/http";
import type { TDatasetStatus, TJob } from "@/types";

export type TSyncPayload = {
  type: "securities" | "daily_bars" | "indicators" | "calendar";
  codes?: string[];
  date_from?: string;
};

export type TJobAccepted = { id: number; job_id: string };

export const datasetsApi = {
  getStatus: () => unwrap<TDatasetStatus>(api.get("datasets/status")),

  triggerSync: (payload: TSyncPayload) =>
    unwrap<TJobAccepted>(api.post("datasets/sync", { json: payload })),

  getJob: (jobId: string) => unwrap<TJob>(api.get(`jobs/${jobId}`)),
};
