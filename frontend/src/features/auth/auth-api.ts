import { api, unwrap } from "@/core/http";
import type { TMe, TTokenResponse } from "@/types";

export type TLoginPayload = { account: string; password: string };
export type TRegisterPayload = { email: string; username?: string; password: string };

export const authApi = {
  login: (payload: TLoginPayload) =>
    unwrap<TTokenResponse>(api.post("auth/login", { json: payload })),

  register: (payload: TRegisterPayload) =>
    unwrap<TTokenResponse>(api.post("auth/register", { json: payload })),

  me: () => unwrap<TMe>(api.get("me")),

  logout: () => unwrap<unknown>(api.post("auth/logout")),
};
