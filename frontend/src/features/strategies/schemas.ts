import { z } from "zod";
import type { TStrategy, TStrategyTemplate } from "@/types";

export const strategyFormSchema = z.object({
  name: z.string().min(1, "请输入策略名称").max(128),
  description: z.string().max(500).optional(),
  universeType: z.enum(["all", "index", "list", "factor"]),
  universeCode: z.string().optional(),
  universeCodes: z.string().optional(),
  signalType: z.enum(["ma_cross", "ma_trend", "factor_rank", "rsi", "bollinger", "macd"]),
  fast: z.coerce.number().int().min(2).max(120).optional(),
  slow: z.coerce.number().int().min(5).max(250).optional(),
  factor: z.string().optional(),
  topPct: z.coerce.number().min(0.01).max(1).optional(),
  rsiPeriod: z.coerce.number().int().min(5).max(60).optional(),
  // ma_trend（趋势金字塔）专用：启动乖离率上限 + 加仓档数/比例 + 初始仓位 + 移动止盈
  biasUpper: z.coerce.number().min(0.02).max(0.3).optional(),
  observeStopLoss: z.coerce.number().min(0.02).max(0.15).optional(),
  observeDays: z.coerce.number().int().min(1).max(10).optional(),
  initWeight: z.coerce.number().min(0.1).max(1).optional(),
  addSteps: z.coerce.number().int().min(0).max(5).optional(),
  addWeight: z.coerce.number().min(0.05).max(1).optional(),
  trailing: z.coerce.number().min(0.05).max(0.3).optional(),
  rebalanceFreq: z.enum(["day", "week", "month"]),
  maxN: z.coerce.number().int().min(1).max(100),
  stopLoss: z.coerce.number().min(0).max(0.5).optional(),
  takeProfit: z.coerce.number().min(0).max(1).optional(),
});

export type TStrategyForm = z.infer<typeof strategyFormSchema>;

function buildMaTrendConfig(values: TStrategyForm): Record<string, unknown> {
  // 趋势金字塔：均线阶梯固定（短期 entry / 中期 add），仅暴露关键旋钮可调。
  return {
    signals: [
      {
        type: "ma_trend",
        launch: {
          bias_ma: 5,
          bias_range: [0.0, values.biasUpper ?? 0.08],
          slope_ma: 5,
          slope_window: 5,
          above_ma: 5,
          above_ratio: 0.8,
          above_window: 10,
        },
        tiers: [
          { mas: [5, 10, 20], role: "entry" },
          { mas: [20, 30, 40], role: "add" },
        ],
        slope_ma: 20,
        slope_window: 5,
      },
    ],
    rebalance: { freq: values.rebalanceFreq },
    position: {
      scheme: "pyramid",
      max_n: values.maxN,
      scale_in: {
        init_weight: values.initWeight ?? 0.2,
        observe_days: values.observeDays ?? 5,
        add_steps: values.addSteps ?? 2,
        add_weight: values.addWeight ?? 0.4,
        trigger: "short_align",
        add_triggers: ["short_align", "medium_align"],
      },
    },
    stop: {
      observe_stop_loss: values.observeStopLoss ?? 0.05,
      ...(values.stopLoss ? { stop_loss: values.stopLoss } : { stop_loss: 0.08 }),
      ...(values.trailing ? { trailing: values.trailing } : {}),
    },
  };
}

export function buildConfigFromForm(values: TStrategyForm): Record<string, unknown> {
  if (values.signalType === "ma_trend") {
    return buildMaTrendConfig(values);
  }

  const signal: Record<string, unknown> = { type: values.signalType };
  if (values.signalType === "ma_cross") {
    signal.fast = values.fast ?? 5;
    signal.slow = values.slow ?? 20;
  } else if (values.signalType === "factor_rank") {
    signal.factor = values.factor || "momentum_20";
    signal.top = values.topPct ?? 0.1;
  } else if (values.signalType === "rsi") {
    signal.period = values.rsiPeriod ?? 14;
    signal.oversold = 30;
    signal.overbought = 70;
  } else if (values.signalType === "bollinger") {
    signal.period = values.rsiPeriod ?? 20;
    signal.std = 2.0;
  }

  const config: Record<string, unknown> = {
    signals: [signal],
    rebalance: { freq: values.rebalanceFreq },
    position: { scheme: "equal_weight", max_n: values.maxN },
  };
  if (values.stopLoss || values.takeProfit) {
    config.stop = {
      ...(values.stopLoss ? { stop_loss: values.stopLoss } : {}),
      ...(values.takeProfit ? { take_profit: values.takeProfit } : {}),
    };
  }
  return config;
}

export function buildUniverseFromForm(values: TStrategyForm) {
  if (values.universeType === "index") {
    return { type: "index" as const, code: values.universeCode || "000300" };
  }
  if (values.universeType === "list") {
    const codes = (values.universeCodes || "")
      .split(/[,，\s]+/)
      .map((c) => c.trim())
      .filter(Boolean);
    return { type: "list" as const, codes };
  }
  return { type: values.universeType };
}

export function formDefaultsFromStrategy(s?: Partial<TStrategyForm>) {
  return {
    name: "",
    description: "",
    universeType: "all" as const,
    universeCode: "000300",
    universeCodes: "",
    signalType: "ma_cross" as const,
    fast: 5,
    slow: 20,
    factor: "momentum_20",
    topPct: 0.1,
    rsiPeriod: 14,
    biasUpper: 0.08,
    observeStopLoss: 0.05,
    observeDays: 5,
    initWeight: 0.2,
    addSteps: 2,
    addWeight: 0.4,
    trailing: 0.12,
    rebalanceFreq: "week" as const,
    maxN: 10,
    stopLoss: 0.08,
    takeProfit: 0.2,
    ...s,
  };
}

export function parseStrategyToForm(strategy: TStrategy): TStrategyForm {
  const sig = strategy.config?.signals?.[0] ?? {};
  const stype = (sig.type as TStrategyForm["signalType"]) || "ma_cross";
  const universe = strategy.universe;
  const scaleIn = (strategy.config?.position?.scale_in ?? {}) as Record<string, number>;
  const launch = (sig.launch ?? {}) as { bias_range?: number[] };
  const biasUpper = launch.bias_range?.[1];

  return formDefaultsFromStrategy({
    name: strategy.name,
    description: strategy.description ?? "",
    universeType: universe?.type ?? "all",
    universeCode: universe?.code ?? "000300",
    universeCodes: universe?.codes?.join(", ") ?? "",
    signalType: stype,
    fast: Number(sig.fast ?? 5),
    slow: Number(sig.slow ?? 20),
    factor: String(sig.factor ?? "momentum_20"),
    topPct: Number(sig.top ?? 0.1),
    rsiPeriod: Number(sig.period ?? 14),
    biasUpper: biasUpper != null ? Number(biasUpper) : 0.08,
    observeStopLoss: strategy.config?.stop?.observe_stop_loss ?? 0.05,
    observeDays: scaleIn.observe_days != null ? Number(scaleIn.observe_days) : 5,
    initWeight: scaleIn.init_weight != null ? Number(scaleIn.init_weight) : 0.2,
    addSteps: scaleIn.add_steps != null ? Number(scaleIn.add_steps) : 2,
    addWeight: scaleIn.add_weight != null ? Number(scaleIn.add_weight) : 0.4,
    trailing: strategy.config?.stop?.trailing ?? 0.12,
    rebalanceFreq: strategy.config?.rebalance?.freq ?? "week",
    maxN: strategy.config?.position?.max_n ?? 10,
    stopLoss: strategy.config?.stop?.stop_loss,
    takeProfit: strategy.config?.stop?.take_profit,
  });
}

export function parseTemplateToForm(tpl: TStrategyTemplate): TStrategyForm {
  const fake: TStrategy = {
    id: 0,
    name: tpl.name,
    type: "config",
    description: tpl.description,
    latest_version: 0,
    config: tpl.config,
    params_schema: tpl.params_schema,
    default_params: tpl.default_params,
    universe: tpl.universe,
  };
  return parseStrategyToForm(fake);
}
