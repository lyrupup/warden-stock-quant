import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Loader2 } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtDateTime, fmtMoney } from "@/core/lib";
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
import { portfoliosApi } from "@/features/portfolios/portfolios-api";
import { tradingApi } from "./trading-api";

export function TradingPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [portfolioId, setPortfolioId] = useState<string>("");
  const [code, setCode] = useState("600000");
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [qty, setQty] = useState("1000");
  const [price, setPrice] = useState("10.5");

  const portfoliosQuery = useQuery({
    queryKey: ["portfolios"],
    queryFn: () => portfoliosApi.list(1, 50),
  });

  const pid = portfolioId ? Number(portfolioId) : null;

  const ordersQuery = useQuery({
    queryKey: ["trading", pid, "orders"],
    queryFn: () => tradingApi.listOrders(pid!, 1, 30),
    enabled: pid != null,
  });

  const tradesQuery = useQuery({
    queryKey: ["trading", pid, "trades"],
    queryFn: () => tradingApi.listTrades(pid!, 1, 30),
    enabled: pid != null,
  });

  const signalsQuery = useQuery({
    queryKey: ["trading", pid, "signals"],
    queryFn: () => tradingApi.listSignals(pid!),
    enabled: pid != null,
  });

  const orderMutation = useMutation({
    mutationFn: () =>
      tradingApi.submitOrder(pid!, {
        code,
        side,
        qty: Number(qty),
        order_type: "limit",
        price: Number(price),
      }),
    onSuccess: () => {
      toast.success("下单成功");
      void qc.invalidateQueries({ queryKey: ["trading", pid] });
      void qc.invalidateQueries({ queryKey: ["portfolios", pid, "positions"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const items = portfoliosQuery.data?.list ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.tradingCenter")}
        description="Paper 仿真交易：手动下单经风控校验后由 PaperGateway 即时撮合，可查看订单、成交与调仓信号。"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            选择组合
            <InfoTip content="仅 Paper 模式组合支持仿真下单；订单会先经过 M9 风控引擎，通过后写入 orders/trades 并更新持仓。" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <select
            className="flex h-10 w-full max-w-md rounded-md border border-input bg-background px-3 py-2 text-sm"
            value={portfolioId}
            onChange={(e) => setPortfolioId(e.target.value)}
          >
            <option value="">请选择仿真组合</option>
            {items.map((p) => (
              <option key={p.id} value={String(p.id)}>
                {p.name}（#{p.id}，现金 {fmtMoney(p.cash)}）
              </option>
            ))}
          </select>
        </CardContent>
      </Card>

      {pid != null && (
        <>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                手动下单
                <InfoTip
                  align="right"
                  content="限价单须填写 price；数量为 100 股整数倍。买入受可用资金约束，卖出受 T+1 可卖数量约束。"
                />
              </CardTitle>
            </CardHeader>
            <CardContent className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              <div className="space-y-2">
                <Label>证券代码</Label>
                <Input value={code} onChange={(e) => setCode(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>方向</Label>
                <select
                  className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
                  value={side}
                  onChange={(e) => setSide(e.target.value as "buy" | "sell")}
                >
                  <option value="buy">买入</option>
                  <option value="sell">卖出</option>
                </select>
              </div>
              <div className="space-y-2">
                <Label>数量（股）</Label>
                <Input value={qty} onChange={(e) => setQty(e.target.value)} />
              </div>
              <div className="space-y-2">
                <Label>限价</Label>
                <Input value={price} onChange={(e) => setPrice(e.target.value)} />
              </div>
              <div className="flex items-end">
                <Button onClick={() => orderMutation.mutate()} disabled={orderMutation.isPending}>
                  提交订单
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>订单</CardTitle>
              </CardHeader>
              <CardContent>
                {ordersQuery.isLoading ? (
                  <Loader2 className="h-6 w-6 animate-spin" />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>代码</TableHead>
                        <TableHead>方向</TableHead>
                        <TableHead>数量</TableHead>
                        <TableHead>状态</TableHead>
                        <TableHead>时间</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(ordersQuery.data?.list ?? []).map((o) => (
                        <TableRow key={o.id}>
                          <TableCell>{o.code}</TableCell>
                          <TableCell>{o.side}</TableCell>
                          <TableCell>{o.filled_qty || o.qty}</TableCell>
                          <TableCell>{o.status}</TableCell>
                          <TableCell>{fmtDateTime(o.created_at)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>成交</CardTitle>
              </CardHeader>
              <CardContent>
                {tradesQuery.isLoading ? (
                  <Loader2 className="h-6 w-6 animate-spin" />
                ) : (
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>代码</TableHead>
                        <TableHead>方向</TableHead>
                        <TableHead>数量</TableHead>
                        <TableHead>金额</TableHead>
                        <TableHead>时间</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {(tradesQuery.data?.list ?? []).map((tr) => (
                        <TableRow key={tr.id}>
                          <TableCell>{tr.code}</TableCell>
                          <TableCell>{tr.side}</TableCell>
                          <TableCell>{tr.qty}</TableCell>
                          <TableCell>{tr.amount ? fmtMoney(tr.amount) : "—"}</TableCell>
                          <TableCell>{fmtDateTime(tr.trade_time)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                调仓信号
                <InfoTip content="对比策略目标仓位与当前持仓的差额，仅作建议不下单；再平衡请在组合页触发。" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              {signalsQuery.isLoading ? (
                <Loader2 className="h-6 w-6 animate-spin" />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>代码</TableHead>
                      <TableHead>方向</TableHead>
                      <TableHead>数量</TableHead>
                      <TableHead>参考价</TableHead>
                      <TableHead>原因</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {(signalsQuery.data ?? []).map((s, i) => (
                      <TableRow key={`${s.code}-${i}`}>
                        <TableCell>{s.code}</TableCell>
                        <TableCell>{s.side}</TableCell>
                        <TableCell>{s.qty}</TableCell>
                        <TableCell>{s.price.toFixed(2)}</TableCell>
                        <TableCell>{s.reason}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
