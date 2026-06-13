import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Ban, Loader2, Plus } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtDateTime, fmtMoney } from "@/core/lib";
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
import type { TBacktest } from "@/types";
import { backtestsApi } from "./backtests-api";
import { BacktestStatusBadge } from "./status-badge";

type TBacktestListProps = {
  onCreate: () => void;
};

export function BacktestList({ onCreate }: TBacktestListProps) {
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["backtests"],
    queryFn: () => backtestsApi.list(1, 50),
    // 列表存在排队/运行中的任务时自动轮询刷新状态
    refetchInterval: (query) => {
      const items = query.state.data?.list ?? [];
      const active = items.some((b) => b.status === "queued" || b.status === "running");
      return active ? 3000 : false;
    },
  });

  const cancelMutation = useMutation({
    mutationFn: backtestsApi.cancel,
    onSuccess: () => {
      toast.success("已请求取消回测");
      void qc.invalidateQueries({ queryKey: ["backtests"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const items = listQuery.data?.list ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>我的回测</CardTitle>
        <Button size="sm" onClick={onCreate}>
          <Plus className="mr-1 h-4 w-4" />
          新建回测
        </Button>
      </CardHeader>
      <CardContent>
        {listQuery.isLoading ? (
          <div className="flex justify-center py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            暂无回测，点击「新建回测」选择策略版本与区间发起回测。
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>策略 / 版本</TableHead>
                <TableHead>区间</TableHead>
                <TableHead>初始资金</TableHead>
                <TableHead>状态</TableHead>
                <TableHead>进度</TableHead>
                <TableHead>创建时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((b: TBacktest) => (
                <TableRow key={b.id}>
                  <TableCell>
                    <Link
                      to={`/backtests/${b.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {b.name ?? `回测 #${b.id}`}
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {b.strategy_name ? (
                      <span>
                        {b.strategy_id ? (
                          <Link
                            to={`/strategies/${b.strategy_id}`}
                            className="text-foreground hover:underline"
                          >
                            {b.strategy_name}
                          </Link>
                        ) : (
                          <span className="text-foreground">{b.strategy_name}</span>
                        )}
                        {b.strategy_version != null && (
                          <span className="ml-1 rounded bg-muted px-1.5 py-0.5 text-xs">
                            v{b.strategy_version}
                          </span>
                        )}
                      </span>
                    ) : (
                      <span className="text-xs">版本 #{b.strategy_version_id}（策略已删除）</span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {b.date_from} ~ {b.date_to}
                  </TableCell>
                  <TableCell>{fmtMoney(b.init_capital)}</TableCell>
                  <TableCell>
                    <BacktestStatusBadge status={b.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {b.status === "running" ? `${Number(b.progress)}%` : "—"}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {fmtDateTime(b.created_at)}
                  </TableCell>
                  <TableCell className="text-right">
                    {(b.status === "queued" || b.status === "running") && (
                      <Button
                        variant="ghost"
                        size="icon"
                        title="取消回测"
                        onClick={() => {
                          if (confirm(`确认取消回测「${b.name ?? b.id}」？`)) {
                            cancelMutation.mutate(b.id);
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
