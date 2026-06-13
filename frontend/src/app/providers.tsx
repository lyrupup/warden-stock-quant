import type { ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { I18nextProvider } from "react-i18next";
import { queryClient } from "@/core/query";
import { ThemeProvider } from "@/core/theme";
import { Toaster } from "@/core/ui";
import { i18n } from "@/core/i18n";

/** 全局 Provider 装配：i18n + Theme + QueryClient + Toaster */
export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <I18nextProvider i18n={i18n}>
      <ThemeProvider>
        <QueryClientProvider client={queryClient}>
          {children}
          <Toaster />
        </QueryClientProvider>
      </ThemeProvider>
    </I18nextProvider>
  );
}
