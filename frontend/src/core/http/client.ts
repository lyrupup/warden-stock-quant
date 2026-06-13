import ky from "ky";
import { useAuthStore } from "@/core/auth/store";
import { ApiError } from "./api-error";
import type { TApiResponse } from "@/types";

const prefixUrl = import.meta.env.VITE_API_BASE ?? "/api/v1";

/** 主请求实例：注入鉴权头，401 触发刷新/登出 */
export const api = ky.create({
  prefixUrl,
  timeout: 30000,
  retry: 0,
  hooks: {
    beforeRequest: [
      (req) => {
        const token = useAuthStore.getState().accessToken;
        if (token) req.headers.set("Authorization", `Bearer ${token}`);
      },
    ],
    afterResponse: [
      async (_req, _opt, res) => {
        if (res.status === 401) {
          await useAuthStore.getState().tryRefreshOrLogout();
        }
        return res;
      },
    ],
  },
});

/**
 * 统一响应解包：{ code, message, data }。
 * code != 0 抛 ApiError；网络/HTTP 异常由 ky 抛出，调用方需 try/catch。
 */
export async function unwrap<T>(p: Promise<Response>): Promise<T> {
  const res = await p;
  const body = (await res.json()) as TApiResponse<T>;
  // JobAccepted(60001) 等非 0 但属正常受理的码由调用方自行处理，这里仅对错误码抛出
  if (body.code !== 0 && body.code !== 60001) {
    throw new ApiError(body.code, body.message ?? "请求失败");
  }
  return body.data;
}
