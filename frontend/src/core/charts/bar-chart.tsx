import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "./echart";

export interface IBarChartProps {
  categories: string[];
  data: number[];
  height?: number | string;
  className?: string;
  seriesName?: string;
}

/** 柱状图（收益分布等） */
export function BarChart({
  categories,
  data,
  height,
  className,
  seriesName = "频次",
}: IBarChartProps) {
  const option = useMemo<EChartsOption>(
    () => ({
      tooltip: { trigger: "axis" },
      grid: { left: 48, right: 16, top: 16, bottom: 48 },
      xAxis: { type: "category", data: categories, axisLabel: { rotate: 45, fontSize: 10 } },
      yAxis: { type: "value", minInterval: 1 },
      series: [{ name: seriesName, type: "bar", data }],
    }),
    [categories, data, seriesName],
  );

  return <EChart option={option} height={height} className={className} />;
}
