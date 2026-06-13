import type { ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Ban, Download, Loader2 } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtDate, fmtMoney, fmtNum, fmtPct, toNum } from "@/core/lib";
import { BarChart, LineChart } from "@/core/charts";
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
import type { TBacktestMetrics, TBacktestStrategy, TReportAnalysis } from "@/types";
import { backtestsApi } from "./backtests-api";
import { BacktestStatusBadge } from "./status-badge";

const FREQ_LABELS: Record<string, string> = {
  day: "每日",
  week: "每周",
  month: "每月",
};

const SCHEME_LABELS: Record<string, string> = {
  equal_weight: "等权分配",
  fixed_fraction: "固定比例",
  pyramid: "金字塔加仓",
  volatility_target: "波动率目标",
};

function StrategySnapshotCard({ backtestId }: { backtestId: number }) {
  const query = useQuery({
    queryKey: ["backtests", backtestId, "strategy"],
    queryFn: () => backtestsApi.strategy(backtestId),
  });

  const s: TBacktestStrategy | undefined = query.data;

  const signalTypes =
    s?.config?.signals?.map((sig) => String(sig.type ?? "未知")).join(" + ") || "—";
  const freq = s?.config?.rebalance?.freq;
  const scheme = s?.config?.position?.scheme;
  const stop = s?.config?.stop;
  const universe = s?.universe;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <CardTitle className="text-base">回测策略快照</CardTitle>
          <InfoTip
            content="回测创建时绑定的策略版本不可变快照。此处展示的是当时实际执行的策略配置，即使该策略之后被修改或删除也不受影响，确保回测结果可复现。"
          />
        </div>
        {s?.version != null && (
          <span className="rounded bg-muted px-2 py-0.5 text-xs">v{s.version}</span>
        )}
      </CardHeader>
      <CardContent>
        {query.isLoading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : !s ? (
          <p className="text-sm text-muted-foreground">暂无策略信息。</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
              <SnapItem
                label="策略"
                hint="该回测使用的策略名称。点击可跳转到策略详情查看当前最新版本。"
                value={
                  s.strategy_name ? (
                    s.strategy_id ? (
                      <Link
                        to={`/strategies/${s.strategy_id}`}
                        className="text-primary hover:underline"
                      >
                        {s.strategy_name}
                      </Link>
                    ) : (
                      s.strategy_name
                    )
                  ) : (
                    `版本 #${s.strategy_version_id}（已删除）`
                  )
                }
              />
              <SnapItem
                label="信号类型"
                hint="策略的入场/出场信号组合，如 ma_cross（双均线交叉）、ma_trend（多头排列趋势）等。"
                value={signalTypes}
              />
              <SnapItem
                label="再平衡频率"
                hint="组合按此频率检查信号并调仓：每日 / 每周 / 每月。"
                value={freq ? FREQ_LABELS[freq] ?? freq : "—"}
              />
              <SnapItem
                label="持仓方案"
                hint="资金在标的间的分配方式，如等权、固定比例、金字塔加仓等。"
                value={scheme ? SCHEME_LABELS[scheme] ?? scheme : "—"}
              />
              {s.config?.position?.max_n != null && (
                <SnapItem
                  label="最大持仓数"
                  hint="组合同时持有的标的数量上限。"
                  value={String(s.config.position.max_n)}
                />
              )}
              {stop?.stop_loss != null && (
                <SnapItem
                  label="止损"
                  hint="单笔持仓相对成本回撤达到该比例时强制卖出。"
                  value={fmtPct(stop.stop_loss)}
                />
              )}
              {stop?.take_profit != null && (
                <SnapItem
                  label="止盈"
                  hint="单笔持仓盈利达到该比例时止盈卖出。"
                  value={fmtPct(stop.take_profit)}
                />
              )}
              {stop?.trailing != null && (
                <SnapItem
                  label="移动止盈"
                  hint="持仓从盈利最高点回落达到该比例时卖出，锁定浮盈。"
                  value={fmtPct(stop.trailing)}
                />
              )}
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex items-center gap-1.5">
                <span className="text-muted-foreground">本次回测股票池：</span>
                <span>{describeUniverse(universe)}</span>
                <InfoTip content="本次回测实际使用的候选标的范围，由创建回测时选定（可覆盖策略默认值），与策略逻辑无关。类型：all 全市场、index 指数成分、list 指定代码列表、factor 因子筛选。" />
              </div>
              {universe?.type === "list" && (universe.codes?.length ?? 0) > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {universe.codes!.map((code) => (
                    <span
                      key={code}
                      className="rounded bg-muted px-2 py-0.5 font-mono text-xs"
                    >
                      {code}
                    </span>
                  ))}
                </div>
              )}
            </div>

            {s.description && (
              <p className="text-sm text-muted-foreground">{s.description}</p>
            )}

            <details className="rounded-lg border bg-muted/30 p-3">
              <summary className="cursor-pointer text-sm text-muted-foreground">
                查看完整策略配置（JSON）
              </summary>
              <pre className="mt-2 overflow-x-auto text-xs leading-relaxed">
                {JSON.stringify(s.config ?? {}, null, 2)}
              </pre>
            </details>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function SnapItem({
  label,
  hint,
  value,
}: {
  label: string;
  hint: string;
  value: ReactNode;
}) {
  return (
    <div className="rounded-lg border p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <span>{label}</span>
        <InfoTip content={hint} />
      </div>
      <div className="mt-1 text-sm font-medium">{value}</div>
    </div>
  );
}

function describeUniverse(u: TBacktestStrategy["universe"]): string {
  if (!u) return "—";
  switch (u.type) {
    case "all":
      return "全市场";
    case "index":
      return `指数成分（${u.code ?? "未指定"}）`;
    case "list":
      return `指定列表（${u.codes?.length ?? 0} 只）`;
    case "factor":
      return "因子筛选";
    default:
      return String(u.type);
  }
}

type TBacktestDetailProps = {
  backtestId: number;
};

type TMetricItem = {
  label: string;
  hint: string;
  value: string;
  tone?: "pos" | "neg";
};

function buildMetricItems(m: TBacktestMetrics, bm?: TReportAnalysis["benchmark_metrics"]): TMetricItem[] {
  const totalReturn = toNum(m.total_return);
  const annual = toNum(m.annual_return);
  const items: TMetricItem[] = [
    {
      label: "总收益率",
      hint: "回测区间内组合净值相对初始资金的累计涨跌幅。",
      value: fmtPct(m.total_return),
      tone: totalReturn >= 0 ? "pos" : "neg",
    },
    {
      label: "年化收益率",
      hint: "将总收益按 252 个交易日折算为每年的复合收益率，便于跨区间比较。",
      value: fmtPct(m.annual_return),
      tone: annual >= 0 ? "pos" : "neg",
    },
    {
      label: "最大回撤",
      hint: "净值从历史最高点回落的最大幅度，衡量策略的下行风险，越接近 0 越好。",
      value: fmtPct(m.max_drawdown),
      tone: "neg",
    },
    {
      label: "夏普比率",
      hint: "单位波动获得的超额收益（年化）。越高代表风险调整后收益越好，>1 较优。",
      value: fmtNum(m.sharpe, 2),
    },
    {
      label: "索提诺比率",
      hint: "只用下行波动计算的夏普变体，更关注亏损风险，越高越好。",
      value: fmtNum(m.sortino, 2),
    },
    {
      label: "卡玛比率",
      hint: "年化收益 ÷ 最大回撤，衡量承受单位回撤换取的收益，越高越好。",
      value: fmtNum(m.calmar, 2),
    },
    {
      label: "年化波动率",
      hint: "日收益标准差的年化值，反映净值波动剧烈程度。",
      value: fmtPct(m.volatility),
    },
    {
      label: "胜率",
      hint: "盈利的平仓交易占全部平仓交易的比例。",
      value: fmtPct(m.win_rate),
    },
    {
      label: "盈亏比",
      hint: "总盈利金额 ÷ 总亏损金额，>1 表示盈利大于亏损。",
      value: fmtNum(m.profit_factor, 2),
    },
    {
      label: "换手率",
      hint: "年化换手，成交额相对资金规模的周转倍数，反映交易频繁程度。",
      value: fmtNum(m.turnover, 2),
    },
    {
      label: "最大回撤区间",
      hint: "出现最大回撤的起止日期（高点 → 低点）。",
      value:
        m.mdd_from && m.mdd_to ? `${fmtDate(m.mdd_from)} ~ ${fmtDate(m.mdd_to)}` : "—",
    },
  ];
  if (bm?.alpha != null) {
    items.push({
      label: "Alpha（年化）",
      hint: "相对基准的超额收益（日收益回归截距年化），衡量选股/择时能力。",
      value: fmtPct(bm.alpha),
      tone: bm.alpha >= 0 ? "pos" : "neg",
    });
  }
  if (bm?.beta != null) {
    items.push({
      label: "Beta",
      hint: "策略收益对基准收益的敏感度。1 表示与基准同步波动，<1 波动更小。",
      value: fmtNum(bm.beta, 2),
    });
  }
  if (bm?.info_ratio != null) {
    items.push({
      label: "信息比率",
      hint: "超额收益均值 ÷ 跟踪误差（年化），衡量相对基准的风险调整后表现。",
      value: fmtNum(bm.info_ratio, 2),
    });
  }
  return items.map((it) => ({
    ...it,
    value: it.value === "NaN" ? "—" : it.value,
  })) as TMetricItem[];
}

export function BacktestDetail({ backtestId }: TBacktestDetailProps) {
  const qc = useQueryClient();

  const btQuery = useQuery({
    queryKey: ["backtests", backtestId],
    queryFn: () => backtestsApi.get(backtestId),
    refetchInterval: (query) => {
      const s = query.state.data?.status;
      return s === "queued" || s === "running" ? 2000 : false;
    },
  });

  const status = btQuery.data?.status;
  const done = status === "succeeded";

  const metricsQuery = useQuery({
    queryKey: ["backtests", backtestId, "metrics"],
    queryFn: () => backtestsApi.metrics(backtestId),
    enabled: done,
  });

  const equityQuery = useQuery({
    queryKey: ["backtests", backtestId, "equity"],
    queryFn: () => backtestsApi.equity(backtestId),
    enabled: done,
  });

  const tradesQuery = useQuery({
    queryKey: ["backtests", backtestId, "trades"],
    queryFn: () => backtestsApi.trades(backtestId, 1, 100),
    enabled: done,
  });

  const analysisQuery = useQuery({
    queryKey: ["backtests", backtestId, "analysis"],
    queryFn: () => backtestsApi.analysis(backtestId),
    enabled: done,
  });

  const downloadReportMutation = useMutation({
    mutationFn: () => backtestsApi.downloadReportHtml(backtestId),
    onSuccess: () => toast.success("报告已下载"),
    onError: (err) => toast.error(describeError(err)),
  });

  const cancelMutation = useMutation({
    mutationFn: () => backtestsApi.cancel(backtestId),
    onSuccess: () => {
      toast.success("已请求取消回测");
      void qc.invalidateQueries({ queryKey: ["backtests", backtestId] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  if (btQuery.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const bt = btQuery.data;
  if (!bt) return null;

  const equity = equityQuery.data ?? [];
  const categories = equity.map((p) => p.trade_date);
  const navSeries = equity.map((p) => toNum(p.nav));
  const benchSeries = equity.map((p) => toNum(p.benchmark_nav));
  const hasBench = benchSeries.some((v) => !Number.isNaN(v));
  const trades = tradesQuery.data?.list ?? [];
  const analysis = analysisQuery.data;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div className="space-y-1">
            <CardTitle>{bt.name ?? `回测 #${bt.id}`}</CardTitle>
            <p className="text-sm text-muted-foreground">
              {bt.date_from} ~ {bt.date_to} · 初始资金 {fmtMoney(bt.init_capital)} · 基准{" "}
              {bt.benchmark}
            </p>
          </div>
          <div className="flex items-center gap-3">
            <BacktestStatusBadge status={bt.status} />
            {done && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => downloadReportMutation.mutate()}
                disabled={downloadReportMutation.isPending}
              >
                {downloadReportMutation.isPending ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Download className="mr-1 h-4 w-4" />
                )}
                导出报告
              </Button>
            )}
            {(bt.status === "queued" || bt.status === "running") && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => cancelMutation.mutate()}
                disabled={cancelMutation.isPending}
              >
                <Ban className="mr-1 h-4 w-4" />
                取消
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {bt.status === "running" || bt.status === "queued" ? (
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              {bt.status === "queued" ? "任务排队中…" : `运行中 ${Number(bt.progress)}%`}
            </div>
          ) : bt.status === "failed" ? (
            <p className="text-sm text-destructive">回测失败：{bt.error ?? "未知错误"}</p>
          ) : bt.status === "canceled" ? (
            <p className="text-sm text-muted-foreground">回测已取消。</p>
          ) : (
            <p className="text-sm text-muted-foreground">回测已完成，下方为绩效与净值表现。</p>
          )}
        </CardContent>
      </Card>

      <StrategySnapshotCard backtestId={backtestId} />

      {done && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="text-base">绩效指标</CardTitle>
            </CardHeader>
            <CardContent>
              {metricsQuery.isLoading || analysisQuery.isLoading ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : metricsQuery.data ? (
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
                  {buildMetricItems(metricsQuery.data, analysis?.benchmark_metrics).map(
                    (it) => (
                    <div key={it.label} className="rounded-lg border p-3">
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <span>{it.label}</span>
                        <InfoTip content={it.hint} />
                      </div>
                      <div
                        className={
                          "mt-1 text-lg font-semibold " +
                          (it.tone === "pos"
                            ? "text-emerald-500"
                            : it.tone === "neg"
                              ? "text-destructive"
                              : "")
                        }
                      >
                        {it.value}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-muted-foreground">暂无指标数据。</p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">净值曲线</CardTitle>
            </CardHeader>
            <CardContent>
              {equityQuery.isLoading ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : equity.length > 0 ? (
                <LineChart
                  categories={categories}
                  height={360}
                  series={[
                    { name: "策略净值", data: navSeries, area: true },
                    ...(hasBench ? [{ name: "基准净值", data: benchSeries }] : []),
                  ]}
                />
              ) : (
                <p className="text-sm text-muted-foreground">暂无净值数据。</p>
              )}
            </CardContent>
          </Card>

          {analysis && (
            <>
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    回撤曲线
                    <InfoTip content="净值相对历史最高点的回落幅度，越接近 0 越好（通常为负值）。" />
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <LineChart
                    categories={analysis.drawdown_series.map((p) => p.trade_date)}
                    height={280}
                    series={[
                      {
                        name: "回撤",
                        data: analysis.drawdown_series.map((p) => toNum(p.drawdown) * 100),
                        area: true,
                      },
                    ]}
                  />
                </CardContent>
              </Card>

              {analysis.rolling_sharpe.some((p) => p.sharpe != null) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      滚动夏普（60 日）
                      <InfoTip content="近 60 个交易日滚动窗口的年化夏普比率，观察策略风险调整收益随时间的变化。" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <LineChart
                      categories={analysis.rolling_sharpe.map((p) => p.trade_date)}
                      height={280}
                      series={[
                        {
                          name: "滚动夏普",
                          data: analysis.rolling_sharpe.map((p) =>
                            p.sharpe == null ? NaN : toNum(p.sharpe),
                          ),
                        },
                      ]}
                    />
                  </CardContent>
                </Card>
              )}

              {analysis.monthly_returns.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      月度收益
                      <InfoTip content="按自然月汇总的组合收益率，便于观察策略的季节性与稳定性。" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>年月</TableHead>
                          <TableHead className="text-right">收益率</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {analysis.monthly_returns.map((row) => (
                          <TableRow key={`${row.year}-${row.month}`}>
                            <TableCell>
                              {row.year}-{String(row.month).padStart(2, "0")}
                            </TableCell>
                            <TableCell
                              className={`text-right ${
                                row.return >= 0 ? "text-emerald-500" : "text-destructive"
                              }`}
                            >
                              {fmtPct(row.return)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )}

              {analysis.return_distribution.some((b) => b.count > 0) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      日收益分布
                      <InfoTip content="每日收益率的直方图分布，可观察收益偏度与尾部风险。" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <BarChart
                      categories={analysis.return_distribution.map(
                        (b) => `${(b.bin_start * 100).toFixed(1)}%`,
                      )}
                      data={analysis.return_distribution.map((b) => b.count)}
                      height={280}
                    />
                  </CardContent>
                </Card>
              )}

              {analysis.stock_attribution.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      个股盈亏贡献
                      <InfoTip content="按卖出成交的已实现盈亏汇总，反映各标的对组合收益的贡献（不含浮盈）。" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>代码</TableHead>
                          <TableHead className="text-right">累计盈亏</TableHead>
                          <TableHead className="text-right">平仓次数</TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {analysis.stock_attribution.map((row) => (
                          <TableRow key={row.code}>
                            <TableCell>{row.code}</TableCell>
                            <TableCell
                              className={`text-right ${
                                row.total_pnl >= 0 ? "text-emerald-500" : "text-destructive"
                              }`}
                            >
                              {fmtMoney(row.total_pnl)}
                            </TableCell>
                            <TableCell className="text-right">{row.trade_count}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </CardContent>
                </Card>
              )}

              {(analysis.concentration.avg_max_weight != null ||
                analysis.concentration.avg_holdings != null) && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center gap-2 text-base">
                      持仓集中度
                      <InfoTip content="日均最大单票权重与平均持股数，反映组合分散程度。" />
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                      {analysis.concentration.avg_max_weight != null && (
                        <div className="rounded-lg border p-3">
                          <p className="text-xs text-muted-foreground">日均最大权重</p>
                          <p className="mt-1 text-lg font-semibold">
                            {fmtPct(analysis.concentration.avg_max_weight)}
                          </p>
                        </div>
                      )}
                      {analysis.concentration.avg_holdings != null && (
                        <div className="rounded-lg border p-3">
                          <p className="text-xs text-muted-foreground">日均持股数</p>
                          <p className="mt-1 text-lg font-semibold">
                            {fmtNum(analysis.concentration.avg_holdings, 1)}
                          </p>
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">交易明细</CardTitle>
            </CardHeader>
            <CardContent>
              {tradesQuery.isLoading ? (
                <div className="flex justify-center py-6">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : trades.length > 0 ? (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>日期</TableHead>
                      <TableHead>代码</TableHead>
                      <TableHead>方向</TableHead>
                      <TableHead className="text-right">价格</TableHead>
                      <TableHead className="text-right">数量</TableHead>
                      <TableHead className="text-right">金额</TableHead>
                      <TableHead className="text-right">盈亏</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {trades.map((t) => (
                      <TableRow key={t.id}>
                        <TableCell>{t.trade_date}</TableCell>
                        <TableCell>{t.code}</TableCell>
                        <TableCell>
                          <span
                            className={
                              t.side === "buy" ? "text-destructive" : "text-emerald-500"
                            }
                          >
                            {t.side === "buy" ? "买入" : "卖出"}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">{fmtNum(t.price)}</TableCell>
                        <TableCell className="text-right">{t.qty}</TableCell>
                        <TableCell className="text-right">{fmtMoney(t.amount)}</TableCell>
                        <TableCell className="text-right">
                          {t.pnl == null ? (
                            "—"
                          ) : (
                            <span
                              className={
                                toNum(t.pnl) >= 0 ? "text-emerald-500" : "text-destructive"
                              }
                            >
                              {fmtMoney(t.pnl)}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground">区间内无成交记录。</p>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
