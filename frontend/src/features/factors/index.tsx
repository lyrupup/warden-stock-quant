import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Loader2, Play, Trash2 } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtNum } from "@/core/lib";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InfoTip,
  PageHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  toast,
} from "@/core/ui";
import { factorsApi } from "./factors-api";

export function FactorsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["factors"],
    queryFn: () => factorsApi.list(1, 50),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      factorsApi.create({
        name: `custom_mom_${Date.now()}`,
        type: "expr",
        expr: "momentum_20",
        direction: 1,
      }),
    onSuccess: () => {
      toast.success("因子已创建");
      void qc.invalidateQueries({ queryKey: ["factors"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const computeMutation = useMutation({
    mutationFn: (id: number) =>
      factorsApi.compute(id, {
        universe: { type: "list", codes: ["600000", "600001"] },
      }),
    onSuccess: () => toast.success("因子计算已入队（测试环境同步执行）"),
    onError: (e) => toast.error(describeError(e)),
  });

  const analyzeMutation = useMutation({
    mutationFn: async (id: number) => {
      const job = await factorsApi.analyze(id, { forward_period: 5, n_quantiles: 5 });
      return factorsApi.getAnalysis(id, job.id);
    },
    onSuccess: (data) => {
      toast.success(`IC 均值 ${fmtNum(data.ic_mean)}，IR ${fmtNum(data.ic_ir)}`);
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: factorsApi.delete,
    onSuccess: () => {
      toast.success("已删除");
      void qc.invalidateQueries({ queryKey: ["factors"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const items = listQuery.data?.list ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.factors")}
        description="因子定义、PIT 计算与 IC/分层检验；合成因子可接入 factor_rank 选股回测。"
        actions={
          <Button size="sm" onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            新建自定义因子
          </Button>
        }
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            因子库
            <InfoTip content="内置因子（如 momentum_20）可直接用于回测 factor_rank 信号；自定义因子需先计算落库。" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          {listQuery.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>类型</TableHead>
                  <TableHead>类别</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((f) => (
                  <TableRow key={`${f.id ?? f.name}`}>
                    <TableCell>{f.name}</TableCell>
                    <TableCell>{f.type}</TableCell>
                    <TableCell>{f.category ?? "—"}</TableCell>
                    <TableCell className="space-x-2 text-right">
                      {f.id && (
                        <>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => computeMutation.mutate(f.id!)}
                          >
                            <Play className="mr-1 h-3 w-3" />
                            计算
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => analyzeMutation.mutate(f.id!)}
                          >
                            IC 分析
                          </Button>
                          {!f.name.startsWith("momentum") && (
                            <Button
                              size="sm"
                              variant="ghost"
                              onClick={() => deleteMutation.mutate(f.id!)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          )}
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
