import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, CheckCircle2, Loader2 } from "lucide-react";
import { fmtDateTime, fmtMoney, fmtNum, fmtPct } from "@/core/lib";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  InfoTip,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/core/ui";
import type { TOptimizationResult } from "@/types";
import { optimizationsApi } from "./backtests-api";
import { BacktestStatusBadge } from "./status-badge";

type TOptimizationDetailProps = {
  optimizationId: number;
};

function MetricCell({ value }: { value?: string | number | null }) {
  if (value == null) return <span className="text-muted-foreground">—</span>;
  return <span>{fmtNum(value, 4)}</span>;
}

function ParamsCell({ params }: { params: Record<string, number | string> }) {
  return (
    <div className="flex flex-wrap gap-1">
      {Object.entries(params).map(([k, v]) => (
        <span key={k} className="rounded bg-muted px-1.5 py-0.5 text-xs font-mono">
          {k}={v}
        </span>
      ))}
    </div>
  );
}

function SummaryCard({
  summary,
  objective,
}: {
  summary: NonNullable<import("@/types").TOptimization["summary"]>;
  objective: string;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          寻优汇总
          <InfoTip content="按样本内目标指标排序的最优参数；若启用样本外拆分，会给出 IS/OOS 一致性与过拟合警告。" />
        </CardTitle>
        <CardDescription>
          目标：{objective} · 共测试 {summary.tested} 组参数
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {summary.best_params && (
          <div>
            <p className="mb-1 text-sm font-medium">最优参数</p>
            <ParamsCell params={summary.best_params as Record<string, number | string>} />
          </div>
        )}
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p className="text-xs text-muted-foreground">样本内 {objective}</p>
            <p className="text-lg font-semibold">{fmtNum(summary.best_value, 4)}</p>
          </div>
          {summary.best_oos_value != null && (
            <div>
              <p className="text-xs text-muted-foreground">样本外 {objective}</p>
              <p className="text-lg font-semibold">{fmtNum(summary.best_oos_value, 4)}</p>
            </div>
          )}
          {summary.stability != null && (
            <div>
              <p className="flex items-center gap-1 text-xs text-muted-foreground">
                参数稳定性
                <InfoTip content="目标值离散度越小，最优解越不孤立，参数平台越稳健。接近 1 表示较稳定。" />
              </p>
              <p className="text-lg font-semibold">{fmtNum(summary.stability, 4)}</p>
            </div>
          )}
        </div>
        {summary.overfit_warning != null && (
          <div
            className={`flex items-start gap-2 rounded-md border p-3 text-sm ${
              summary.overfit_warning
                ? "border-destructive/50 bg-destructive/5 text-destructive"
                : "border-green-500/50 bg-green-500/5 text-green-700 dark:text-green-400"
            }`}
          >
            {summary.overfit_warning ? (
              <>
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>
                  过拟合风险提示：样本外表现与样本内差异较大，最优参数可能过度拟合历史数据，建议扩大样本外区间或缩小参数空间。
                </span>
              </>
            ) : (
              <>
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <span>样本内外表现基本一致，最优参数具有一定泛化能力。</span>
              </>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ResultsTable({ rows, objective }: { rows: TOptimizationResult[]; objective: string }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">参数组合排名</CardTitle>
        <CardDescription>按样本内 {objective} 降序排列；含样本内/外关键指标对比。</CardDescription>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>排名</TableHead>
              <TableHead>参数</TableHead>
              <TableHead>
                <span className="flex items-center gap-1">
                  IS {objective}
                  <InfoTip content="样本内（In-Sample）区间上的目标指标值，用于排序选优。" />
                </span>
              </TableHead>
              <TableHead>
                <span className="flex items-center gap-1">
                  OOS {objective}
                  <InfoTip content="样本外（Out-of-Sample）区间上的目标指标，用于检验泛化能力。" />
                </span>
              </TableHead>
              <TableHead>IS 夏普</TableHead>
              <TableHead>IS 最大回撤</TableHead>
              <TableHead>OOS 夏普</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.id} className={r.rank === 1 ? "bg-muted/40" : undefined}>
                <TableCell className="font-medium">#{r.rank}</TableCell>
                <TableCell>
                  <ParamsCell params={r.params} />
                </TableCell>
                <TableCell>
                  <MetricCell value={r.objective_value} />
                </TableCell>
                <TableCell>
                  <MetricCell
                    value={
                      r.oos_metrics
                        ? (r.oos_metrics[objective as keyof typeof r.oos_metrics] as
                            | string
                            | number
                            | undefined)
                        : null
                    }
                  />
                </TableCell>
                <TableCell>
                  <MetricCell value={r.is_metrics?.sharpe} />
                </TableCell>
                <TableCell>
                  <MetricCell value={r.is_metrics?.max_drawdown} />
                </TableCell>
                <TableCell>
                  <MetricCell value={r.oos_metrics?.sharpe} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

export function OptimizationDetail({ optimizationId }: TOptimizationDetailProps) {
  const detailQuery = useQuery({
    queryKey: ["optimizations", optimizationId],
    queryFn: () => optimizationsApi.get(optimizationId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "queued" || status === "running" ? 3000 : false;
    },
  });

  const resultsQuery = useQuery({
    queryKey: ["optimizations", optimizationId, "results"],
    queryFn: () => optimizationsApi.results(optimizationId),
    enabled: detailQuery.data?.status === "succeeded",
  });

  const opt = detailQuery.data;

  if (detailQuery.isLoading) {
    return (
      <div className="flex justify-center py-12 text-muted-foreground">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (!opt) {
    return <p className="py-8 text-center text-muted-foreground">寻优任务不存在</p>;
  }

  const isActive = opt.status === "queued" || opt.status === "running";

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <CardTitle>{opt.name ?? `寻优 #${opt.id}`}</CardTitle>
            <BacktestStatusBadge status={opt.status} />
          </div>
          <CardDescription>
            {opt.strategy_name && (
              <span>
                策略 {opt.strategy_name}
                {opt.strategy_version != null && ` v${opt.strategy_version}`}
                {" · "}
              </span>
            )}
            {opt.date_from} ~ {opt.date_to} · {fmtMoney(opt.init_capital)} ·{" "}
            {opt.method === "grid" ? "网格" : "随机"}搜索 · 目标 {opt.objective} ·{" "}
            {opt.total_combos} 组
            {Number(opt.oos_split) > 0 && ` · OOS ${fmtPct(Number(opt.oos_split) * 100, 0)}`}
          </CardDescription>
        </CardHeader>
        {isActive && (
          <CardContent>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              正在批量回测 {opt.total_combos} 组参数… {Number(opt.progress)}%
            </div>
          </CardContent>
        )}
        {opt.error && (
          <CardContent>
            <p className="text-sm text-destructive">{opt.error}</p>
          </CardContent>
        )}
        {opt.finished_at && (
          <CardContent className="pt-0 text-xs text-muted-foreground">
            完成于 {fmtDateTime(opt.finished_at)}
          </CardContent>
        )}
      </Card>

      {opt.summary && (
        <SummaryCard summary={opt.summary} objective={opt.objective} />
      )}

      {resultsQuery.isLoading && opt.status === "succeeded" && (
        <div className="flex justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </div>
      )}

      {resultsQuery.data && resultsQuery.data.length > 0 && (
        <ResultsTable rows={resultsQuery.data} objective={opt.objective} />
      )}
    </div>
  );
}
