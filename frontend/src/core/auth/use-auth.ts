import { useAuthStore } from "./store";
import { ERole } from "@/types";

/** 鉴权信息便捷 hook */
export function useAuth() {
  const accessToken = useAuthStore((s) => s.accessToken);
  const user = useAuthStore((s) => s.user);
  const setSession = useAuthStore((s) => s.setSession);
  const setUser = useAuthStore((s) => s.setUser);
  const logout = useAuthStore((s) => s.logout);

  return {
    accessToken,
    user,
    isAuthenticated: !!accessToken,
    isAdmin: user?.role === ERole.Admin,
    setSession,
    setUser,
    logout,
  };
}
