import { useTranslation } from "react-i18next";
import { FlaskConical, LineChart as LineIcon, Briefcase, BellRing } from "lucide-react";
import { useAuth } from "@/core/auth";
import { LineChart } from "@/core/charts";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  PageHeader,
} from "@/core/ui";

const STAT_CARDS = [
  { key: "strategies", labelKey: "nav.strategies", icon: LineIcon },
  { key: "backtests", labelKey: "nav.backtests", icon: FlaskConical },
  { key: "portfolios", labelKey: "nav.portfolios", icon: Briefcase },
  { key: "alerts", labelKey: "nav.alerts", icon: BellRing },
] as const;

/** 概览仪表盘占位：统计卡 + 净值曲线示意（后续接入真实数据） */
export function DashboardPage() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const categories = ["01-02", "01-09", "01-16", "01-23", "01-30", "02-06", "02-13"];
  const demoSeries = [
    { name: "组合净值", data: [1, 1.02, 0.99, 1.05, 1.08, 1.04, 1.12], area: true },
    { name: "沪深300", data: [1, 1.01, 1.0, 1.02, 1.03, 1.01, 1.04] },
  ];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.dashboard")}
        description={`欢迎回来${user?.username ? `，${user.username}` : ""}。这里汇总你的策略、回测、组合与告警概要。`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {STAT_CARDS.map((c) => (
          <Card key={c.key}>
            <CardHeader className="flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium text-muted-foreground">
                {t(c.labelKey)}
              </CardTitle>
              <c.icon className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-semibold">—</div>
              <p className="text-xs text-muted-foreground">{t("common.inDevelopment")}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle>净值走势</CardTitle>
          <CardDescription>示意数据，待回测/组合接入后替换为真实净值与基准对比。</CardDescription>
        </CardHeader>
        <CardContent>
          <LineChart categories={categories} series={demoSeries} height={320} />
        </CardContent>
      </Card>
    </div>
  );
}
