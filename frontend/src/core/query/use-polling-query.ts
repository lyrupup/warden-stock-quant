import { useQuery } from "@tanstack/react-query";
import { api, unwrap } from "@/core/http";
import { EJobStatus, type TJob } from "@/types";

const TERMINAL: EJobStatus[] = [EJobStatus.Succeeded, EJobStatus.Failed, EJobStatus.Canceled];

/**
 * 异步任务进度轮询：提交后用 job_id 轮询 jobs/{id}，
 * 终态（succeeded/failed/canceled）后停止轮询。
 */
export function useJobQuery(jobId?: string, intervalMs = 2000) {
  return useQuery({
    queryKey: ["job", jobId],
    queryFn: () => unwrap<TJob>(api.get(`jobs/${jobId}`)),
    enabled: !!jobId,
    refetchInterval: (q) => (TERMINAL.includes(q.state.data?.status as EJobStatus) ? false : intervalMs),
  });
}
