import { Toaster as SonnerToaster, toast } from "sonner";
import { useThemeStore } from "@/core/theme";

/** 全局 Toaster，主题跟随 useThemeStore */
export function Toaster() {
  const theme = useThemeStore((s) => s.theme);
  return <SonnerToaster theme={theme} richColors position="top-right" closeButton />;
}

export { toast };
