import { api, unwrap } from "@/core/http";
import type { TApiKey, TApiKeyCreated, TPageData } from "@/types";

export type TCreateApiKeyPayload = { name: string; scopes: string[] };

export const accountApi = {
  listApiKeys: () => unwrap<TPageData<TApiKey> | TApiKey[]>(api.get("api-keys")),

  createApiKey: (payload: TCreateApiKeyPayload) =>
    unwrap<TApiKeyCreated>(api.post("api-keys", { json: payload })),

  revokeApiKey: (id: number) => unwrap<unknown>(api.delete(`api-keys/${id}`)),
};

/** 兼容后端可能返回数组或分页结构 */
export function normalizeApiKeys(data: TPageData<TApiKey> | TApiKey[] | undefined): TApiKey[] {
  if (!data) return [];
  return Array.isArray(data) ? data : (data.list ?? []);
}
