import type { TBacktestStatus } from "@/types";
import { Badge } from "@/core/ui";

const STATUS_META: Record<
  TBacktestStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "success" | "warning" }
> = {
  queued: { label: "排队中", variant: "secondary" },
  running: { label: "运行中", variant: "warning" },
  succeeded: { label: "已完成", variant: "success" },
  failed: { label: "失败", variant: "destructive" },
  canceled: { label: "已取消", variant: "secondary" },
};

export function BacktestStatusBadge({ status }: { status: TBacktestStatus }) {
  const meta = STATUS_META[status] ?? STATUS_META.queued;
  return <Badge variant={meta.variant}>{meta.label}</Badge>;
}

export function backtestStatusLabel(status: TBacktestStatus): string {
  return (STATUS_META[status] ?? STATUS_META.queued).label;
}
