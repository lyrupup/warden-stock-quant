import { type ReactNode } from "react";
import { Loader2 } from "lucide-react";
import { useSession } from "@/features/auth";

/** 登录后/刷新后恢复会话（拉取 /me），加载期间显示占位 */
export function SessionBootstrap({ children }: { children: ReactNode }) {
  const { isLoading } = useSession();
  if (isLoading) {
    return (
      <div className="flex h-screen items-center justify-center text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        加载中…
      </div>
    );
  }
  return <>{children}</>;
}
