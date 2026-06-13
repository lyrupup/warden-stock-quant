import { type ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { useAuth } from "@/core/auth";
import { ERole } from "@/types";

/** 受保护路由：未登录跳 /login（记录来源以便登录后回跳） */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth();
  const location = useLocation();
  if (!isAuthenticated) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }
  return <>{children}</>;
}

/** 角色路由：要求指定角色，否则跳 403 */
export function RequireRole({ role, children }: { role: ERole; children: ReactNode }) {
  const { user, isAdmin } = useAuth();
  const allowed = role === ERole.Admin ? isAdmin : !!user;
  if (!allowed) return <Navigate to="/403" replace />;
  return <>{children}</>;
}
