import { useEffect, type ReactNode } from "react";
import { useThemeStore } from "./store";

/** 将主题应用到 <html class>，并响应切换 */
export function ThemeProvider({ children }: { children: ReactNode }) {
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("dark", theme === "dark");
    root.classList.toggle("light", theme === "light");
  }, [theme]);

  return <>{children}</>;
}
