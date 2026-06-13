import { QueryClient } from "@tanstack/react-query";
import { ApiError, ErrorCode } from "@/core/http";

/** 全局 QueryClient：401 由 http 层处理，业务错误不重试 */
export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        if (error instanceof ApiError) return false;
        return failureCount < 2;
      },
      staleTime: 30_000,
      refetchOnWindowFocus: false,
    },
    mutations: {
      retry: false,
    },
  },
});

export { ErrorCode };
