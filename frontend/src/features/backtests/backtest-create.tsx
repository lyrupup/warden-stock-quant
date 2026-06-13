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
import { backtestsApi } from "./backtests-api";

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
    universeType: z.enum(["all", "index", "list"]).default("all"),
    universeCode: z.string().optional(),
    universeCodes: z.string().optional(),
    commissionRate: z.coerce.number().min(0).default(0.0003),
    stampTaxRate: z.coerce.number().min(0).default(0.0005),
    slippageValue: z.coerce.number().min(0).default(0.0005),
  })
  .refine((v) => v.dateFrom <= v.dateTo, {
    message: "开始日期不能晚于结束日期",
    path: ["dateTo"],
  });

type TForm = z.infer<typeof schema>;

export function BacktestCreate() {
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
      universeType: "all",
      universeCode: "",
      universeCodes: "",
      commissionRate: 0.0003,
      stampTaxRate: 0.0005,
      slippageValue: 0.0005,
    },
  });

  const strategies = strategiesQuery.data?.list ?? [];
  const versions = useMemo(() => versionsQuery.data ?? [], [versionsQuery.data]);

  // 选定策略后，默认选中最新版本
  useEffect(() => {
    if (versions.length > 0) {
      form.setValue("versionId", versions[0].id);
    }
  }, [versions, form]);

  const versionId = form.watch("versionId");

  // 选中版本后，用该版本的「默认股票池」预填表单（用户仍可修改，回测以表单值为准）
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
      const codes = (values.universeCodes ?? "")
        .split(/[,\s]+/)
        .map((c) => c.trim())
        .filter(Boolean);
      // 股票池以表单为权威来源：本次回测真正使用的范围
      const universe =
        values.universeType === "list"
          ? { type: "list" as const, codes }
          : values.universeType === "index"
            ? { type: "index" as const, code: (values.universeCode ?? "").trim() }
            : { type: "all" as const };
      return backtestsApi.create({
        name: values.name || undefined,
        strategy_version_id: values.versionId,
        date_from: values.dateFrom,
        date_to: values.dateTo,
        init_capital: values.initCapital,
        benchmark: values.benchmark,
        adjust: values.adjust,
        universe,
        cost_config: {
          commission_rate: values.commissionRate,
          stamp_tax_rate: values.stampTaxRate,
          slippage_type: "pct",
          slippage_value: values.slippageValue,
        },
      });
    },
    onSuccess: (data) => {
      toast.success("回测已提交，正在后台运行");
      navigate(`/backtests/${data.id}`);
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const errors = form.formState.errors;

  return (
    <Card className="max-w-3xl">
      <CardHeader>
        <CardTitle>新建回测</CardTitle>
        <CardDescription>选择已保存的策略版本，设定区间、资金与成本后提交异步回测。</CardDescription>
      </CardHeader>
      <CardContent>
        <form
          className="space-y-5"
          onSubmit={form.handleSubmit((v) => createMutation.mutate(v))}
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel hint="选择要回测的策略；策略需先在「策略管理」中创建并保存。仅支持配置式策略。">
                策略
              </FieldLabel>
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
              <FieldLabel hint="策略的不可变版本快照。回测绑定具体版本以保证结果可复现，默认选最新版本。">
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
              {errors.versionId && (
                <p className="text-sm text-destructive">{errors.versionId.message}</p>
              )}
            </div>
          </div>

          <div className="space-y-2">
            <FieldLabel hint="回测任务的自定义名称，便于在列表中区分；留空则自动命名。">
              回测名称
            </FieldLabel>
            <Input placeholder="（可选）如：双均线-2024复盘" {...form.register("name")} />
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel htmlFor="dateFrom" hint="回测起始交易日。引擎会额外预读约 120 天数据用于均线等指标预热。">
                开始日期
              </FieldLabel>
              <Input id="dateFrom" type="date" {...form.register("dateFrom")} />
              {errors.dateFrom && (
                <p className="text-sm text-destructive">{errors.dateFrom.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <FieldLabel htmlFor="dateTo" hint="回测结束交易日。区间过长会增加计算耗时，单次上限约 10 年。">
                结束日期
              </FieldLabel>
              <Input id="dateTo" type="date" {...form.register("dateTo")} />
              {errors.dateTo && (
                <p className="text-sm text-destructive">{errors.dateTo.message}</p>
              )}
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <FieldLabel hint="回测起始的虚拟现金，按此基数计算净值与收益率，如 1000000 表示 100 万。">
                初始资金
              </FieldLabel>
              <Input type="number" step="10000" {...form.register("initCapital")} />
              {errors.initCapital && (
                <p className="text-sm text-destructive">{errors.initCapital.message}</p>
              )}
            </div>
            <div className="space-y-2">
              <FieldLabel hint="对比基准指数代码，用于在净值曲线中叠加基准走势，默认 000300（沪深300）。">
                基准
              </FieldLabel>
              <Input {...form.register("benchmark")} />
            </div>
            <div className="space-y-2">
              <FieldLabel hint="复权口径：qfq 前复权（默认）/ hfq 后复权 / 空为不复权。回测内须保持口径一致。">
                复权
              </FieldLabel>
              <select
                className="flex h-10 w-full rounded-md border border-input bg-background px-3 text-sm"
                {...form.register("adjust")}
              >
                <option value="qfq">前复权</option>
                <option value="hfq">后复权</option>
                <option value="">不复权</option>
              </select>
            </div>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <FieldLabel hint="本次回测实际使用的股票池，默认带入所选策略版本的「默认股票池」，可在此修改。这是回测真正生效的选股范围，与策略逻辑解耦。全市场 / 指数成分 / 自定义列表。">
                股票池（默认取自策略，可修改）
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
            {form.watch("universeType") === "index" && (
              <div className="space-y-2">
                <FieldLabel hint="指数代码，如 000300（沪深300）、000905（中证500），以其成分股作为选股范围。">
                  指数代码
                </FieldLabel>
                <Input placeholder="000300" {...form.register("universeCode")} />
              </div>
            )}
            {form.watch("universeType") === "list" && (
              <div className="space-y-2 sm:col-span-2">
                <FieldLabel hint="手动指定的股票代码，用逗号或空格分隔，如 600000, 000001。">
                  股票代码（逗号分隔）
                </FieldLabel>
                <Input placeholder="600000, 000001" {...form.register("universeCodes")} />
              </div>
            )}
          </div>

          <div className="grid gap-4 sm:grid-cols-3">
            <div className="space-y-2">
              <FieldLabel hint="买卖双边佣金费率，如 0.0003 表示万分之三；不足最低佣金按最低收取。">
                佣金费率
              </FieldLabel>
              <Input type="number" step="0.0001" {...form.register("commissionRate")} />
            </div>
            <div className="space-y-2">
              <FieldLabel hint="卖出单边收取的印花税率，如 0.0005 表示千分之五（A 股现行标准）。">
                印花税率
              </FieldLabel>
              <Input type="number" step="0.0001" {...form.register("stampTaxRate")} />
            </div>
            <div className="space-y-2">
              <FieldLabel hint="按成交价百分比模拟的滑点，如 0.0005 表示买入加 0.05%、卖出减 0.05%，贴近真实成交。">
                滑点
              </FieldLabel>
              <Input type="number" step="0.0001" {...form.register("slippageValue")} />
            </div>
          </div>

          <div className="flex gap-2">
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? (
                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-1 h-4 w-4" />
              )}
              提交回测
            </Button>
            <Button type="button" variant="outline" onClick={() => navigate("/backtests")}>
              取消
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
