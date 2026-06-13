import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { describeError } from "@/core/http";
import { fmtNum, fmtPct } from "@/core/lib";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InfoTip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  toast,
} from "@/core/ui";
import { backtestsApi, reportsApi } from "./backtests-api";

export function BacktestComparePanel() {
  const [selected, setSelected] = useState<number[]>([]);

  const listQuery = useQuery({
    queryKey: ["backtests", "compare-picker"],
    queryFn: () => backtestsApi.list(1, 50),
  });

  const compareMutation = useMutation({
    mutationFn: () => reportsApi.compare(selected),
    onError: (err) => toast.error(describeError(err)),
  });

  const succeeded = (listQuery.data?.list ?? []).filter((b) => b.status === "succeeded");

  const toggle = (id: number) => {
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : prev.length < 10 ? [...prev, id] : prev,
    );
  };

  const rows = compareMutation.data?.rows ?? [];

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            选择回测（2–10 个已完成）
            <InfoTip content="勾选多个已完成的回测，并排对比年化收益、夏普、最大回撤与 Alpha/Beta 等关键指标。" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-2">
            {succeeded.map((b) => (
              <Button
                key={b.id}
                size="sm"
                variant={selected.includes(b.id!) ? "default" : "outline"}
                onClick={() => toggle(b.id!)}
              >
                #{b.id} {b.name ?? "未命名"}
              </Button>
            ))}
          </div>
          <Button
            disabled={selected.length < 2 || compareMutation.isPending}
            onClick={() => compareMutation.mutate()}
          >
            开始对比
          </Button>
        </CardContent>
      </Card>

      {rows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>对比结果</CardTitle>
          </CardHeader>
          <CardContent className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>回测</TableHead>
                  <TableHead>策略</TableHead>
                  <TableHead>年化</TableHead>
                  <TableHead>夏普</TableHead>
                  <TableHead>最大回撤</TableHead>
                  <TableHead>Alpha</TableHead>
                  <TableHead>Beta</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.backtest_id}>
                    <TableCell>
                      #{r.backtest_id} {r.name ?? ""}
                    </TableCell>
                    <TableCell>
                      {r.strategy_name ?? "—"} v{r.strategy_version ?? "—"}
                    </TableCell>
                    <TableCell>{fmtPct(r.metrics?.annual_return)}</TableCell>
                    <TableCell>{fmtNum(r.metrics?.sharpe)}</TableCell>
                    <TableCell>{fmtPct(r.metrics?.max_drawdown)}</TableCell>
                    <TableCell>{fmtNum(r.benchmark_metrics?.alpha)}</TableCell>
                    <TableCell>{fmtNum(r.benchmark_metrics?.beta)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
