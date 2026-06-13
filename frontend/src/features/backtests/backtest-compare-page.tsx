import { PageHeader } from "@/core/ui";
import { BacktestComparePanel } from "./backtest-compare";

export function BacktestComparePage() {
  return (
    <div className="space-y-6">
      <PageHeader
        title="多回测对比"
        description="并排比较多个已完成回测的核心绩效与基准相对指标，辅助参数与策略选型。"
      />
      <BacktestComparePanel />
    </div>
  );
}
