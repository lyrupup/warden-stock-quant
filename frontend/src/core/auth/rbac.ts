import { ERole, type TMe } from "@/types";

/** 基于角色的访问控制：判断用户是否具备所需角色 */
export function canAccess(user: TMe | null, required?: ERole): boolean {
  if (!required) return !!user;
  if (!user) return false;
  if (user.role === ERole.Admin) return true; // admin 拥有全部权限
  return user.role === required;
}
