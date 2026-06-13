import { create } from "zustand";
import { persist } from "zustand/middleware";
import ky from "ky";
import { ERole, type TMe, type TTokenResponse, type TApiResponse } from "@/types";

const prefixUrl = import.meta.env.VITE_API_BASE ?? "/api/v1";

/** 不带鉴权拦截的裸实例，专用于刷新，避免与主 client 循环依赖/递归 401 */
const bareApi = ky.create({ prefixUrl, timeout: 15000, retry: 0 });

type TAuthState = {
  accessToken: string | null;
  refreshToken: string | null;
  user: TMe | null;
  /** 是否完成初始化（用于路由首屏判断） */
  hydrated: boolean;
};

type TAuthActions = {
  setSession: (tokens: TTokenResponse) => void;
  setUser: (user: TMe | null) => void;
  logout: () => void;
  /** 401 时尝试用 refresh_token 刷新，失败则登出 */
  tryRefreshOrLogout: () => Promise<boolean>;
  isAuthenticated: () => boolean;
  hasRole: (role: ERole) => boolean;
};

export const useAuthStore = create<TAuthState & TAuthActions>()(
  persist(
    (set, get) => ({
      accessToken: null,
      refreshToken: null,
      user: null,
      hydrated: false,

      setSession: (tokens) =>
        set({ accessToken: tokens.access_token, refreshToken: tokens.refresh_token }),

      setUser: (user) => set({ user }),

      logout: () => set({ accessToken: null, refreshToken: null, user: null }),

      tryRefreshOrLogout: async () => {
        const refreshToken = get().refreshToken;
        if (!refreshToken) {
          get().logout();
          return false;
        }
        try {
          const body = await bareApi
            .post("auth/refresh", { json: { refresh_token: refreshToken } })
            .json<TApiResponse<TTokenResponse>>();
          if (body.code !== 0 || !body.data?.access_token) {
            get().logout();
            return false;
          }
          get().setSession(body.data);
          return true;
        } catch {
          get().logout();
          return false;
        }
      },

      isAuthenticated: () => !!get().accessToken,
      hasRole: (role) => get().user?.role === role,
    }),
    {
      name: "wsq-auth",
      partialize: (s) => ({
        accessToken: s.accessToken,
        refreshToken: s.refreshToken,
        user: s.user,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) state.hydrated = true;
      },
    },
  ),
);
