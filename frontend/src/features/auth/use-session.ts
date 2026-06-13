import { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAuth, useAuthStore } from "@/core/auth";
import { authApi } from "./auth-api";

/**
 * 会话引导：已登录但本地无用户信息时拉取 /me 回填 store。
 * 用于刷新页面后恢复当前用户与角色。
 */
export function useSession() {
  const { accessToken, user } = useAuth();
  const setUser = useAuthStore((s) => s.setUser);

  const query = useQuery({
    queryKey: ["me"],
    queryFn: authApi.me,
    enabled: !!accessToken && !user,
    retry: false,
    staleTime: 5 * 60_000,
  });

  useEffect(() => {
    if (query.data) setUser(query.data);
  }, [query.data, setUser]);

  return { isLoading: query.isLoading && !!accessToken && !user };
}
