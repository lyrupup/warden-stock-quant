import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Loader2, RefreshCw, Trash2 } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtMoney } from "@/core/lib";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  InfoTip,
  Input,
  Label,
  PageHeader,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  toast,
} from "@/core/ui";
import { portfoliosApi } from "./portfolios-api";

export function PortfoliosPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [name, setName] = useState("我的仿真组合");
  const [capital, setCapital] = useState("1000000");
  const [strategyVersionId, setStrategyVersionId] = useState("");

  const listQuery = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => portfoliosApi.list(1, 50),
  });

  const positionsQuery = useQuery({
    queryKey: ["portfolios", selectedId, "positions"],
    queryFn: () => portfoliosApi.positions(selectedId!),
    enabled: selectedId != null,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      portfoliosApi.create({
        name,
        init_capital: Number(capital),
        strategy_version_id: strategyVersionId ? Number(strategyVersionId) : undefined,
        rebalance: "week",
      }),
    onSuccess: (p) => {
      toast.success("组合已创建");
      setSelectedId(p.id);
      void qc.invalidateQueries({ queryKey: ["portfolios"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const rebalanceMutation = useMutation({
    mutationFn: portfoliosApi.rebalance,
    onSuccess: (data) => {
      toast.success(data.message);
      void qc.invalidateQueries({ queryKey: ["portfolios", selectedId, "positions"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: portfoliosApi.delete,
    onSuccess: () => {
      toast.success("已删除");
      setSelectedId(null);
      void qc.invalidateQueries({ queryKey: ["portfolios"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const items = listQuery.data?.list ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.portfolios")}
        description="仿真组合：关联策略版本、跟踪持仓与资金，支持再平衡生成目标仓位。"
      />

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              新建组合
              <InfoTip content="Paper 模式使用虚拟资金；再平衡会经 M9 风控校验后由 PaperGateway 执行买卖订单（100 股取整）。" />
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>初始资金</Label>
              <Input value={capital} onChange={(e) => setCapital(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label>策略版本 ID（可选）</Label>
              <Input
                value={strategyVersionId}
                onChange={(e) => setStrategyVersionId(e.target.value)}
                placeholder="在策略页查看版本 ID"
              />
            </div>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              创建
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>我的组合</CardTitle>
          </CardHeader>
          <CardContent>
            {listQuery.isLoading ? (
              <Loader2 className="h-6 w-6 animate-spin" />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>名称</TableHead>
                    <TableHead>现金</TableHead>
                    <TableHead className="text-right">操作</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((p) => (
                    <TableRow key={p.id} className={selectedId === p.id ? "bg-muted/50" : ""}>
                      <TableCell>{p.name}</TableCell>
                      <TableCell>{fmtMoney(p.cash)}</TableCell>
                      <TableCell className="space-x-2 text-right">
                        <Button size="sm" variant="outline" onClick={() => setSelectedId(p.id)}>
                          查看
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => rebalanceMutation.mutate(p.id)}
                        >
                          <RefreshCw className="mr-1 h-3 w-3" />
                          再平衡
                        </Button>
                        <Button size="sm" variant="ghost" onClick={() => deleteMutation.mutate(p.id)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedId && (
        <Card>
          <CardHeader>
            <CardTitle>持仓 #{selectedId}</CardTitle>
          </CardHeader>
          <CardContent>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>代码</TableHead>
                  <TableHead>数量</TableHead>
                  <TableHead>市值</TableHead>
                  <TableHead>盈亏</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(positionsQuery.data ?? []).map((pos) => (
                  <TableRow key={pos.id}>
                    <TableCell>{pos.code}</TableCell>
                    <TableCell>{pos.qty}</TableCell>
                    <TableCell>{fmtMoney(pos.market_value)}</TableCell>
                    <TableCell>{fmtMoney(pos.pnl)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
