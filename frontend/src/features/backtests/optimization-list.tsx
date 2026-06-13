import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Ban, Loader2, Plus } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtDateTime } from "@/core/lib";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  toast,
} from "@/core/ui";
import type { TOptimization } from "@/types";
import { optimizationsApi } from "./backtests-api";
import { BacktestStatusBadge } from "./status-badge";

type TOptimizationListProps = {
  onCreate: () => void;
};

export function OptimizationList({ onCreate }: TOptimizationListProps) {
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["optimizations"],
    queryFn: () => optimizationsApi.list(1, 50),
    refetchInterval: (query) => {
      const items = query.state.data?.list ?? [];
      const active = items.some((o) => o.status === "queued" || o.status === "running");
      return active ? 3000 : false;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: optimizationsApi.cancel,
    onSuccess: () => {
      toast.success("已请求取消寻优");
      void qc.invalidateQueries({ queryKey: ["optimizations"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const items = listQuery.data?.list ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>参数寻优</CardTitle>
        <Button size="sm" onClick={onCreate}>
          <Plus className="mr-1 h-4 w-4" />
          新建寻优
        </Button>
      </CardHeader>
      <CardContent>
        {listQuery.isLoading ? (
          <div className="flex justify-center py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            暂无寻优任务。选择策略版本与参数空间，批量回测并自动排序最优参数组合。
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>策略 / 版本</TableHead>
                <TableHead>方法 / 目标</TableHead>
                <TableHead>组合数</TableHead>
                <TableHead>区间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((o: TOptimization) => (
                <TableRow key={o.id}>
                  <TableCell>
                    <Link
                      to={`/optimizations/${o.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {o.name ?? `寻优 #${o.id}`}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {o.strategy_name ? (
                      <span>
                        <span className="text-foreground">{o.strategy_name}</span>
                        {o.strategy_version != null && (
                          <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs">
                            v{o.strategy_version}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-xs">版本 #{o.strategy_version_id}</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {o.method === "grid" ? "网格" : "随机"} / {o.objective}
                  </TableCell>
                  <TableCell>{o.total_combos}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {o.date_from} ~ {o.date_to}
                  </TableCell>
                  <TableCell>
                    <BacktestStatusBadge status={o.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {fmtDateTime(o.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    {(o.status === "queued" || o.status === "running") && (
                      <Button
                        variant="ghost"
                        size="icon"
                        title="取消寻优"
                        onClick={() => {
                          if (confirm(`确认取消寻优「${o.name ?? o.id}」？`)) {
                            cancelMutation.mutate(o.id);
                          }
                        }}
                      >
                        <Ban className="h-4 w-4 text-destructive" />
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
