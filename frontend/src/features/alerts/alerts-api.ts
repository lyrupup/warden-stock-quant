import { api, unwrap } from "@/core/http";
import type { TPageData } from "@/types";

export type TAlertChannel = {
  id: number;
  type: string;
  config: Record<string, string>;
  enabled: boolean;
  created_at: string;
};

export type TAlertRecord = {
  id: number;
  level: string;
  source?: string;
  title: string;
  body?: string;
  sent: boolean;
  created_at: string;
};

export const alertsApi = {
  listChannels: () => unwrap<TAlertChannel[]>(api.get("alerts/channels")),

  createChannel: (payload: { type: string; config: Record<string, string> }) =>
    unwrap<TAlertChannel>(api.post("alerts/channels", { json: payload })),

  deleteChannel: (id: number) => unwrap<null>(api.delete(`alerts/channels/${id}`)),

  listAlerts: (page = 1, size = 20) =>
    unwrap<TPageData<TAlertRecord>>(api.get("alerts", { searchParams: { page, size } })),
};
