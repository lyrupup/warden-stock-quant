import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { CheckCircle2, Loader2, Save, ShieldCheck } from "lucide-react";
import { describeError } from "@/core/http";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  InfoTip,
  Input,
  Label,
  toast,
} from "@/core/ui";
import type { TStrategyTemplate } from "@/types";
import { strategiesApi } from "./strategies-api";
import {
  buildConfigFromForm,
  buildUniverseFromForm,
  formDefaultsFromStrategy,
  parseStrategyToForm,
  parseTemplateToForm,
  strategyFormSchema,
  type TStrategyForm,
} from "./schemas";

type TStrategyEditorProps = {
  strategyId?: number;
  template?: TStrategyTemplate;
};

/** 表单项标题 + info 提示。 */
function FieldLabel({
  children,
  hint,
  htmlFor,
}: {
  children: ReactNode;
  hint: string;
  htmlFor?: string;
}) {
  return (
    <div className="flex items-center gap-1.5">
      <Label htmlFor={htmlFor}>{children}</Label>
      <InfoTip content={hint} />
    </div>
  );
}

export function StrategyEditor({ strategyId, template }: TStrategyEditorProps) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const isNew = !strategyId;
  const [validateErrors, setValidateErrors] = useState<string[]>([]);

  const detailQuery = useQuery({
    queryKey: ["strategies", strategyId],
    queryFn: () => strategiesApi.get(strategyId!),
    enabled: !!strategyId,
  });

  const versionsQuery = useQuery({
    queryKey: ["strategies", strategyId, "versions"],
    queryFn: () => strategiesApi.versions(strategyId!),
    enabled: !!strategyId,
  });

  const defaultValues = useMemo(() => {
    if (template) return parseTemplateToForm(template);
    if (detailQuery.data) return parseStrategyToForm(detailQuery.data);
    return formDefaultsFromStrategy();
  }, [template, detailQuery.data]);

  const form = useForm<TStrategyForm>({
    resolver: zodResolver(strategyFormSchema),
    defaultValues,
  });

  useEffect(() => {
    form.reset(defaultValues);
  }, [defaultValues, form]);

  const saveMutation = useMutation({
    mutationFn: async (values: TStrategyForm) => {
      const payload = {
        name: values.name,
        type: "config" as const,
        description: values.description,
        config: buildConfigFromForm(values),
        universe: buildUniverseFromForm(values),
        params_schema: detailQuery.data?.params_schema,
        default_params: detailQuery.data?.default_params,
      };
      if (isNew) return strategiesApi.create(payload);
      return strategiesApi.update(strategyId!, payload);
    },
    onSuccess: (data) => {
      toast.success(isNew ? "策略已创建" : "已保存新版本");
      void qc.invalidateQueries({ queryKey: ["strategies"] });
      if (isNew) navigate(`/strategies/${data.id}`, { replace: true });
      else {
        void qc.invalidateQueries({ queryKey: ["strategies", strategyId] });
        void qc.invalidateQueries({ queryKey: ["strategies", strategyId, "versions"] });
      }
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const validateMutation = useMutation({
    mutationFn: async (values: TStrategyForm) => {
      const payload = {
        type: "config" as const,
        config: buildConfigFromForm(values),
        universe: buildUniverseFromForm(values),
      };
      if (!strategyId) {
        return { valid: true, errors: [] as string[] };
      }
      return strategiesApi.validate(strategyId, payload);
    },
    onSuccess: (result) => {
      setValidateErrors(result.errors);
      if (result.valid) {
        toast.success(strategyId ? "服务端校验通过" : "表单校验通过，保存后可进行服务端深度校验");
      } else {
        toast.error("校验未通过，请检查配置");
      }
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const watchAll = form.watch();
  const configPreview = JSON.stringify(
    {
      universe: buildUniverseFromForm(watchAll as TStrategyForm),
      ...buildConfigFromForm(watchAll as TStrategyForm),
    },
    null,
    2,
  );

  if (!isNew && detailQuery.isLoading) {
    return (
      <div className="flex justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="grid gap-6 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle>{isNew ? "新建配置式策略" : `编辑策略 · v${detailQuery.data?.latest_version ?? 1}`}</CardTitle>
          <CardDescription>
            通过表单配置信号积木、股票池与再平衡规则；保存将生成不可变新版本。
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form
            className="space-y-5"
            onSubmit={form.handleSubmit((v) => saveMutation.mutate(v))}
          >
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2 sm:col-span-2">
                <FieldLabel htmlFor="name" hint="策略的唯一名称（同一用户下不可重名），用于在列表与回测中识别。">
                  策略名称
                </FieldLabel>
                <Input id="name" {...form.register("name")} />
                {form.formState.errors.name && (
                  <p className="text-sm text-destructive">{form.formState.errors.name.message}</p>
                )}
              </div>
              <div className="space-y-2 sm:col-span-2">
                <FieldLabel htmlFor="description" hint="策略说明，便于回顾设计意图，不影响信号计算。">
                  描述
                </FieldLabel>
                <Input id="description" {...form.register("description")} />
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <FieldLabel hint="策略的选股范围：全市场、指数成分股，或自定义股票列表。">
                  股票池
                </FieldLabel>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  {...form.register("universeType")}
                >
                  <option value="all">全市场</option>
                  <option value="index">指数成分</option>
                  <option value="list">自定义列表</option>
                </select>
              </div>
              {watchAll.universeType === "index" && (
                <div className="space-y-2">
                  <FieldLabel hint="指数代码，如 000300（沪深300）、000905（中证500）。成分股将作为选股范围。">
                    指数代码
                  </FieldLabel>
                  <Input placeholder="000300" {...form.register("universeCode")} />
                </div>
              )}
              {watchAll.universeType === "list" && (
                <div className="space-y-2 sm:col-span-2">
                  <FieldLabel hint="手动指定的股票代码，用逗号或空格分隔，如 600000, 000001。">
                    股票代码（逗号分隔）
                  </FieldLabel>
                  <Input placeholder="600000, 000001" {...form.register("universeCodes")} />
                </div>
              )}
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-2">
                <FieldLabel hint="生成买卖信号的核心逻辑积木：均线交叉、均线多头排列趋势、因子排名、RSI、布林带等。">
                  信号类型
                </FieldLabel>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  {...form.register("signalType")}
                >
                  <option value="ma_cross">双均线交叉</option>
                  <option value="ma_trend">均线多头排列趋势（金字塔加仓）</option>
                  <option value="factor_rank">因子排名选股</option>
                  <option value="rsi">RSI 超买超卖</option>
                  <option value="bollinger">布林带</option>
                </select>
              </div>
              <div className="space-y-2">
                <FieldLabel hint="按多大频率重新计算信号并调整持仓：每日 / 每周 / 每月。频率越高交易越频繁。">
                  再平衡频率
                </FieldLabel>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                  {...form.register("rebalanceFreq")}
                >
                  <option value="day">每日</option>
                  <option value="week">每周</option>
                  <option value="month">每月</option>
                </select>
              </div>
            </div>

            {watchAll.signalType === "ma_cross" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <FieldLabel hint="短周期均线天数（如 5）。上穿慢线为金叉买入信号。须小于慢线周期。">
                    快线周期
                  </FieldLabel>
                  <Input type="number" {...form.register("fast")} />
                </div>
                <div className="space-y-2">
                  <FieldLabel hint="长周期均线天数（如 20）。快线下穿为死叉卖出信号。">
                    慢线周期
                  </FieldLabel>
                  <Input type="number" {...form.register("slow")} />
                </div>
              </div>
            )}

            {watchAll.signalType === "factor_rank" && (
              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-2">
                  <FieldLabel hint="用于打分排名的因子名，如 momentum_20（20日动量）。按该因子对股票池排序选股。">
                    因子名
                  </FieldLabel>
                  <Input {...form.register("factor")} />
                </div>
                <div className="space-y-2">
                  <FieldLabel hint="选取因子排名靠前的比例（0~1），如 0.1 表示买入排名前 10% 的股票。">
                    选取比例 Top
                  </FieldLabel>
                  <Input type="number" step="0.01" {...form.register("topPct")} />
                </div>
              </div>
            )}

            {watchAll.signalType === "ma_trend" && (
              <div className="space-y-4 rounded-md border border-dashed p-4">
                <p className="text-sm text-muted-foreground">
                  趋势金字塔：启动建 20% 观察仓（沿 MA5 稳步推升）→ 短期多头打开后两步各加 40% →
                  观察期止损更严，确认后启用移动止盈。
                </p>
                <div className="grid gap-4 sm:grid-cols-3">
                  <div className="space-y-2">
                    <FieldLabel hint="启动阶段允许的最大乖离率（收盘价高出 MA5 的比例）。如 0.08 表示偏离 MA5 不超过 8%，避免追高。">
                      启动乖离率上限
                    </FieldLabel>
                    <Input type="number" step="0.01" {...form.register("biasUpper")} />
                  </div>
                  <div className="space-y-2">
                    <FieldLabel hint="观察仓专用止损（比正式仓更严）。如 0.05 表示观察期内回撤 5% 即止损离场。">
                      观察仓止损
                    </FieldLabel>
                    <Input type="number" step="0.01" {...form.register("observeStopLoss")} />
                  </div>
                  <div className="space-y-2">
                    <FieldLabel hint="建观察仓后等待短期多头排列打开的最长天数；超时仍未打开则不再加仓。">
                      观察天数上限
                    </FieldLabel>
                    <Input type="number" {...form.register("observeDays")} />
                  </div>
                  <div className="space-y-2">
                    <FieldLabel hint="启动阶段建立的初始观察仓占比，如 0.2 表示先建 20% 仓位试探。">
                      观察仓比例
                    </FieldLabel>
                    <Input type="number" step="0.05" {...form.register("initWeight")} />
                  </div>
                  <div className="space-y-2">
                    <FieldLabel hint="多头趋势确认后的分批加仓次数。如 2 表示分两步加仓（短期排列 + 中期排列各一次）。">
                      加仓档数（每档 40%）
                    </FieldLabel>
                    <Input type="number" {...form.register("addSteps")} />
                  </div>
                  <div className="space-y-2">
                    <FieldLabel hint="每次加仓增加的仓位占比，如 0.4 表示每档加 40%。注意：观察仓 + 各档加仓总和不得超过 100%。">
                      每档加仓比例
                    </FieldLabel>
                    <Input type="number" step="0.05" {...form.register("addWeight")} />
                  </div>
                  <div className="space-y-2">
                    <FieldLabel hint="移动止盈：从持仓最高点回撤超过该比例即止盈离场，如 0.12 表示回撤 12% 兑现利润。">
                      移动止盈
                    </FieldLabel>
                    <Input type="number" step="0.01" {...form.register("trailing")} />
                  </div>
                </div>
              </div>
            )}

            <div className="grid gap-4 sm:grid-cols-3">
              <div className="space-y-2">
                <FieldLabel hint="同时持有的最大股票数量，用于分散与等权分配，如 10 表示最多持有 10 只。">
                  最大持仓数
                </FieldLabel>
                <Input type="number" {...form.register("maxN")} />
              </div>
              <div className="space-y-2">
                <FieldLabel hint="固定止损比例：单只持仓亏损超过该比例即卖出，如 0.08 表示亏 8% 止损。">
                  止损比例
                </FieldLabel>
                <Input type="number" step="0.01" {...form.register("stopLoss")} />
              </div>
              <div className="space-y-2">
                <FieldLabel hint="固定止盈比例：单只持仓盈利超过该比例即卖出，如 0.2 表示赚 20% 止盈。留空则不启用。">
                  止盈比例
                </FieldLabel>
                <Input type="number" step="0.01" {...form.register("takeProfit")} />
              </div>
            </div>

            <div className="flex flex-wrap gap-2">
              <Button type="submit" disabled={saveMutation.isPending}>
                {saveMutation.isPending ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <Save className="mr-1 h-4 w-4" />
                )}
                保存
              </Button>
              <Button
                type="button"
                variant="outline"
                disabled={validateMutation.isPending}
                onClick={form.handleSubmit((v) => validateMutation.mutate(v))}
              >
                {validateMutation.isPending ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <ShieldCheck className="mr-1 h-4 w-4" />
                )}
                校验配置
              </Button>
            </div>

            {validateErrors.length > 0 && (
              <ul className="rounded-md border border-destructive/30 bg-destructive/5 p-3 text-sm text-destructive">
                {validateErrors.map((e) => (
                  <li key={e}>• {e}</li>
                ))}
              </ul>
            )}
          </form>
        </CardContent>
      </Card>

      <div className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">配置预览</CardTitle>
          </CardHeader>
          <CardContent>
            <pre className="max-h-80 overflow-auto rounded-md bg-muted p-3 text-xs">
              {configPreview}
            </pre>
          </CardContent>
        </Card>

        {!isNew && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">版本历史</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {(versionsQuery.data ?? []).map((v) => (
                <div
                  key={v.id}
                  className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm"
                >
                  <CheckCircle2 className="h-4 w-4 text-muted-foreground" />
                  <span>v{v.version}</span>
                  <span className="ml-auto text-muted-foreground">
                    {v.created_at ? new Date(v.created_at).toLocaleString() : ""}
                  </span>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
