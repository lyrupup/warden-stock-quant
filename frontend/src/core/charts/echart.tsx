import { useEffect, useRef } from "react";
import * as echarts from "echarts";
import { useThemeStore } from "@/core/theme";

export interface IEChartProps {
  option: echarts.EChartsOption;
  height?: number | string;
  className?: string;
}

/** ECharts 基础封装：负责实例化、resize、主题与销毁 */
export function EChart({ option, height = 320, className }: IEChartProps) {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);
  const theme = useThemeStore((s) => s.theme);

  useEffect(() => {
    if (!ref.current) return;
    instRef.current = echarts.init(ref.current, theme === "dark" ? "dark" : undefined);
    const onResize = () => instRef.current?.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      instRef.current?.dispose();
      instRef.current = null;
    };
  }, [theme]);

  useEffect(() => {
    instRef.current?.setOption(option, true);
  }, [option]);

  return (
    <div
      ref={ref}
      className={className}
      style={{ width: "100%", height: typeof height === "number" ? `${height}px` : height }}
    />
  );
}
