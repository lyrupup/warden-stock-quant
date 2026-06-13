import { Info } from "lucide-react";
import { cn } from "@/core/lib";

type TInfoTipProps = {
  /** 提示完整文案 */
  content: string;
  /** 自定义图标容器样式 */
  className?: string;
  /** 提示气泡宽度，默认 w-64 */
  bubbleClassName?: string;
  /**
   * 气泡相对图标的水平对齐：
   * - center（默认）：以图标为中心展开
   * - right：气泡右边缘对齐图标，向左展开（适合图标贴近容器右侧的场景，避免溢出）
   * - left：气泡左边缘对齐图标，向右展开
   */
  align?: "center" | "right" | "left";
};

const ALIGN_CLASS: Record<NonNullable<TInfoTipProps["align"]>, string> = {
  center: "left-1/2 -translate-x-1/2",
  right: "right-0",
  left: "left-0",
};

/**
 * 轻量信息提示：Info 图标 + hover 气泡（纯 CSS group-hover，无额外依赖）。
 * 用于表单项标题、列表描述等需要补充说明的场景。
 */
export function InfoTip({
  content,
  className,
  bubbleClassName,
  align = "center",
}: TInfoTipProps) {
  return (
    <span
      className={cn("group/infotip relative inline-flex shrink-0 align-middle", className)}
      onClick={(e) => e.stopPropagation()}
      onKeyDown={(e) => e.stopPropagation()}
      role="presentation"
    >
      <Info
        className="h-3.5 w-3.5 cursor-help text-muted-foreground transition-colors hover:text-foreground"
        aria-label="说明"
      />
      <span
        className={cn(
          "pointer-events-none absolute bottom-full z-50 mb-2 hidden max-w-[min(18rem,calc(100vw-3rem))] whitespace-normal rounded-md border bg-popover px-3 py-2 text-xs font-normal leading-relaxed text-popover-foreground shadow-md group-hover/infotip:block",
          ALIGN_CLASS[align],
          bubbleClassName ?? "w-64",
        )}
        role="tooltip"
      >
        {content}
      </span>
    </span>
  );
}
