import { useMemo } from "react";
import type { EChartsOption } from "echarts";
import { EChart } from "./echart";

export interface ILineSeries {
  name: string;
  /** 已转 number 的数据点（decimal 字符串请先经 toNum） */
  data: number[];
  area?: boolean;
}

export interface ILineChartProps {
  categories: (string | number)[];
  series: ILineSeries[];
  height?: number | string;
  className?: string;
}

/**
 * 通用折线图（净值/回撤等）。后续填充具体业务数据，
 * decimal 字符串须先经 core/lib toNum 转 number 再传入。
 */
export function LineChart({ categories, series, height, className }: ILineChartProps) {
  const option = useMemo<EChartsOption>(
    () => ({
      tooltip: { trigger: "axis" },
      legend: { data: series.map((s) => s.name), top: 0 },
      grid: { left: 48, right: 16, top: 32, bottom: 32 },
      xAxis: { type: "category", boundaryGap: false, data: categories },
      yAxis: { type: "value", scale: true },
      series: series.map((s) => ({
        name: s.name,
        type: "line",
        smooth: true,
        showSymbol: false,
        areaStyle: s.area ? {} : undefined,
        data: s.data,
      })),
    }),
    [categories, series],
  );

  return <EChart option={option} height={height} className={className} />;
}
