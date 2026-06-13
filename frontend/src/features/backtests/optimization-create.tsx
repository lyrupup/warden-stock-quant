import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { Loader2, Play } from "lucide-react";
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
import { strategiesApi } from "@/features/strategies/strategies-api";
import { optimizationsApi } from "./backtests-api";

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

const schema = z
  .object({
    name: z.string().optional(),
    strategyId: z.coerce.number().int().positive({ message: "请选择策略" }),
    versionId: z.coerce.number().int().positive({ message: "请选择版本" }),
    dateFrom: z.string().min(1, "请选择开始日期"),
    dateTo: z.string().min(1, "请选择结束日期"),
    initCapital: z.coerce.number().positive("初始资金需大于 0"),
    benchmark: z.string().default("000300"),
    adjust: z.enum(["qfq", "hfq", ""]).default("qfq"),
    method: z.enum(["grid", "random"]).default("grid"),
    nIter: z.coerce.number().int().min(1).max(500).default(20),
    objective: z.string().default("sharpe"),
    oosSplit: z.coerce.number().min(0).max(0.8).default(0.3),
    paramSpaceJson: z.string().min(2, "请填写参数空间 JSON"),
    universeType: z.enum(["all", "index", "list"]).default("all"),
    universeCode: z.string().optional(),
    universeCodes: z.string().optional(),
  })
  .refine((v) => v.dateFrom <= v.dateTo, {
    message: "开始日期不能晚于结束日期",
    path: ["dateTo"],
  });

type TForm = z.infer<typeof schema>;

const DEFAULT_PARAM_SPACE = `{
  "fast": [3, 5, 8],
  "slow": [15, 20, 30]
}`;

export function OptimizationCreate() {
  const navigate = useNavigate();
  const [strategyId, setStrategyId] = useState<number | undefined>();

  const strategiesQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: () => strategiesApi.list(1, 100),
  });

  const versionsQuery = useQuery({
    queryKey: ["strategies", strategyId, "versions"],
    queryFn: () => strategiesApi.versions(strategyId!),
    enabled: !!strategyId,
  });

  const form = useForm<TForm>({
    resolver: zodResolver(schema),
    defaultValues: {
      name: "",
      dateFrom: "",
      dateTo: "",
      initCapital: 1000000,
      benchmark: "000300",
      adjust: "qfq",
      method: "grid",
      nIter: 20,
      objective: "sharpe",
      oosSplit: 0.3,
      paramSpaceJson: DEFAULT_PARAM_SPACE,
      universeType: "all",
      universeCode: "",
      universeCodes: "",
    },
  });

  const strategies = strategiesQuery.data?.list ?? [];
  const versions = useMemo(() => versionsQuery.data ?? [], [versionsQuery.data]);

  useEffect(() => {
    if (versions.length > 0) {
      form.setValue("versionId", versions[0].id);
    }
  }, [versions, form]);

  const versionId = form.watch("versionId");

  useEffect(() => {
    const v = versions.find((x) => x.id === Number(versionId));
    const u = v?.universe;
    if (!u) return;
    form.setValue("universeType", (u.type as "all" | "index" | "list") ?? "all");
    form.setValue("universeCode", u.code ?? "");
    form.setValue("universeCodes", (u.codes ?? []).join(", "));
  }, [versionId, versions, form]);

  const createMutation = useMutation({
    mutationFn: async (values: TForm) => {
      let paramSpace: Record<string, (number | string)[]>;
      try {
        paramSpace = JSON.parse(values.paramSpaceJson) as Record<string, (number | string)[]>;
      } catch {
        throw new Error("参数空间 JSON 格式无效");
      }
      const codes = (values.universeCodes ?? "")
        .split(/[,\s]+/)
        .map((c) => c.trim())
        .filter(Boolean);
      const universe =
        values.universeType === "list"
          ? { type: "list" as const, codes }
          : values.universeType === "index"
            ? { type: "index" as const, code: (values.universeCode ?? "").trim() }
            : { type: "all" as const };
      return optimizationsApi.create({
        name: values.name || undefined,
        strategy_version_id: values.versionId,
        param_space: paramSpace,
        method: values.method,
        n_iter: values.nIter,
        objective: values.objective,
        oos_split: values.oosSplit,
        date_from: values.dateFrom,
        date_to: values.dateTo,
        init_capital: values.initCapital,
        benchmark: values.benchmark,
        adjust: values.adjust,
        universe,
      });
    },
    onSuccess: (data) => {
      toast.success("寻优任务已提交");
      navigate(`/optimizations/${data.id}`);
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const errors = form.formState.errors;
  const method = form.watch("method");

  return (
    <Card className="max-w-3xl">
      <CardHeader>
        <CardTitle>新建参数寻优</CardTitle>
        <CardDescription>
          对策略参数做网格或随机搜索，批量回测并按目标指标排序；支持样本内外拆分与过拟合提示。
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-5"
          onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel hint="选择要寻优的策略；仅支持配置式策略。">策略</FieldLabel>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                {...form.register("strategyId", {
                  onChange: (e) => setStrategyId(Number(e.target.value) || undefined),
                })}
              >
                <option value="">请选择策略</option>
                {strategies.map((s) => (
                  <option key={s.id} value={s.id}>
                    {s.name}
                  </option>
                ))}
              </select>
              {errors.strategyId && (
                <p className="text-sm text-destructive">{errors.strategyId.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <FieldLabel hint="寻优绑定的策略版本快照，保证参数空间与信号类型一致。">
                策略版本
              </FieldLabel>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                disabled={!strategyId || versions.length === 0}
                {...form.register("versionId")}
              >
                {versions.map((v) => (
                  <option key={v.id} value={v.id}>
                    v{v.version}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="space-y-2">
            <FieldLabel hint='待搜索的参数及其候选值，JSON 格式。如双均线：{"fast":[3,5,8],"slow":[15,20,30]}。网格搜索会取笛卡尔积，组合数上限 200。'>
              参数空间（JSON）
            </FieldLabel>
            <textarea
              className="flex min-h-[120px] w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-sm"
              {...form.register("paramSpaceJson")}
            />
            {errors.paramSpaceJson && (
              <p className="text-sm text-destructive">{errors.paramSpaceJson.message}</p>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <FieldLabel hint="grid=遍历全部组合；random=从组合中随机抽样 n_iter 组，适合大空间。">
                搜索方法
              </FieldLabel>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                {...form.register("method")}
              >
                <option value="grid">网格搜索</option>
                <option value="random">随机搜索</option>
              </select>
            </div>
            {method === "random" && (
              <div className="space-y-2">
                <FieldLabel hint="随机搜索时抽样的参数组合数量，上限 500。">
                  抽样次数
                </FieldLabel>
                <Input type="number" {...form.register("nIter")} />
              </div>
            )}
            <div className="space-y-2">
              <FieldLabel hint="排序依据：sharpe（夏普）、sortino、calmar、total_return、max_drawdown 等。">
                优化目标
              </FieldLabel>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                {...form.register("objective")}
              >
                <option value="sharpe">夏普比率</option>
                <option value="sortino">索提诺比率</option>
                <option value="calmar">卡玛比率</option>
                <option value="total_return">累计收益</option>
                <option value="annual_return">年化收益</option>
                <option value="max_drawdown">最大回撤</option>
              </select>
            </div>
            <div className="space-y-2">
              <FieldLabel hint="样本外比例，如 0.3 表示后 30% 交易日作为 OOS 验证，用于过拟合诊断；0 表示不拆分。">
                样本外比例
              </FieldLabel>
              <Input type="number" step="0.05" min={0} max={0.8} {...form.register("oosSplit")} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel htmlFor="dateFrom" hint="寻优回测的起始交易日。">
                开始日期
              </FieldLabel>
              <Input id="dateFrom" type="date" {...form.register("dateFrom")} />
            </div>
            <div className="space-y-2">
              <FieldLabel htmlFor="dateTo" hint="寻优回测的结束交易日。">
                结束日期
              </FieldLabel>
              <Input id="dateTo" type="date" {...form.register("dateTo")} />
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel hint="每组参数回测的初始资金。">初始资金</FieldLabel>
              <Input type="number" step="10000" {...form.register("initCapital")} />
            </div>
            <div className="space-y-2">
              <FieldLabel hint="本次寻优使用的股票池，默认取自策略版本。">
                股票池类型
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
          </div>

          {form.watch("universeType") === "list" && (
            <div className="space-y-2">
              <FieldLabel hint="逗号分隔的股票代码。">股票代码</FieldLabel>
              <Input placeholder="600000, 000001" {...form.register("universeCodes")} />
            </div>
          )}

          <div className="flex gap-2">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-1 h-4 w-4" />
              )}
              提交寻优
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate("/optimizations")}>
              取消
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
