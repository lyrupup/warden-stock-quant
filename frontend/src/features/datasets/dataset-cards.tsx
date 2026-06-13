import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Database, Loader2, RefreshCw } from "lucide-react";
import { describeError } from "@/core/http";
import { useJobQuery } from "@/core/query";
import { EJobStatus } from "@/types";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  toast,
} from "@/core/ui";
import { datasetsApi } from "./datasets-api";

export function DatasetStatusCard() {
  const statusQuery = useQuery({
    queryKey: ["datasets", "status"],
    queryFn: datasetsApi.getStatus,
    refetchInterval: 30_000,
  });
  const data = statusQuery.data;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Database className="h-5 w-5" />
          数据集状态
        </CardTitle>
        <CardDescription>本地行情数据集新鲜度与缺口检测</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        {statusQuery.isLoading ? (
          <div className="flex items-center gap-2 text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            加载中…
          </div>
        ) : data ? (
          <>
            <div className="grid gap-2 sm:grid-cols-2">
              <div>
                <span className="text-muted-foreground">最新交易日：</span>
                {data.latest_trade_date ?? "—"}
              </div>
              <div>
                <span className="text-muted-foreground">日 K 更新至：</span>
                {data.bars_updated_to ?? "—"}
              </div>
              <div>
                <span className="text-muted-foreground">证券数量：</span>
                {data.securities_count}
              </div>
              <div>
                <span className="text-muted-foreground">数据陈旧：</span>
                <Badge variant={data.stale ? "destructive" : "secondary"}>
                  {data.stale ? "是" : "否"}
                </Badge>
              </div>
            </div>
            {data.gaps.length > 0 && (
              <div className="flex flex-wrap gap-2">
                <span className="text-muted-foreground">缺口：</span>
                {data.gaps.map((g) => (
                  <Badge key={g} variant="outline">
                    {g}
                  </Badge>
                ))}
              </div>
            )}
          </>
        ) : (
          <p className="text-muted-foreground">暂无数据</p>
        )}
      </CardContent>
    </Card>
  );
}

export function DatasetSyncCard() {
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<string | undefined>();

  const syncMutation = useMutation({
    mutationFn: (type: "securities" | "daily_bars") =>
      datasetsApi.triggerSync({ type }),
    onSuccess: (data) => {
      setJobId(data.job_id);
      toast.success("同步任务已入队");
      void qc.invalidateQueries({ queryKey: ["datasets", "status"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const jobQuery = useJobQuery(jobId);
  const job = jobQuery.data;
  const running =
    job?.status === EJobStatus.Queued || job?.status === EJobStatus.Running;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <RefreshCw className="h-5 w-5" />
          数据同步
        </CardTitle>
        <CardDescription>
          从 warden-stock-data 拉取证券列表与日 K（需管理员配置数据源凭证）
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-wrap gap-3">
        <Button
          disabled={syncMutation.isPending || running}
          onClick={() => syncMutation.mutate("securities")}
        >
          {syncMutation.isPending ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : null}
          同步证券列表
        </Button>
        <Button
          variant="outline"
          disabled={syncMutation.isPending || running}
          onClick={() => syncMutation.mutate("daily_bars")}
        >
          增量同步日 K
        </Button>
        {job && (
          <div className="w-full text-sm text-muted-foreground">
            任务 {job.id.slice(0, 8)}… · 状态 {job.status}
            {job.progress != null ? ` · 进度 ${job.progress}%` : ""}
            {job.error ? ` · 错误：${job.error}` : ""}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
