import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Loader2, Trash2 } from "lucide-react";
import { describeError } from "@/core/http";
import { fmtDateTime } from "@/core/lib";
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
import { riskApi, type TRiskRule } from "./risk-api";

export function RiskPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [name, setName] = useState("我的风控规则");
  const [blacklist, setBlacklist] = useState("600000,000001");
  const [maxAmount, setMaxAmount] = useState("500000");

  const ruleSetsQuery = useQuery({
    queryKey: ["risk-rule-sets"],
    queryFn: () => riskApi.listRuleSets(1, 30),
  });

  const eventsQuery = useQuery({
    queryKey: ["risk-events"],
    queryFn: () => riskApi.listEvents(1, 30),
  });

  const createMutation = useMutation({
    mutationFn: () => {
      const codes = blacklist
        .split(/[,，\s]+/)
        .map((c) => c.trim())
        .filter(Boolean);
      const rules: TRiskRule[] = [
        { type: "blacklist", params: { codes }, action: "reject", enabled: true },
        {
          type: "max_order_amount",
          params: { max: Number(maxAmount) || 500000 },
          action: "reject",
          enabled: true,
        },
      ];
      return riskApi.createRuleSet({ name, scope: "portfolio", rules });
    },
    onSuccess: () => {
      toast.success("规则集已创建");
      void qc.invalidateQueries({ queryKey: ["risk-rule-sets"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: riskApi.deleteRuleSet,
    onSuccess: () => {
      toast.success("已删除");
      void qc.invalidateQueries({ queryKey: ["risk-rule-sets"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.risk")}
        description="配置组合级风控规则集（黑名单、单笔限额等），查看拒单与拦截事件。"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            新建规则集
            <InfoTip content="规则集可绑定到组合（risk_rule_set_id）；下单时会与平台默认规则（可交易/ST/单笔限额）叠加校验。" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label>名称</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-1">
                黑名单代码
                <InfoTip content="逗号分隔的 6 位证券代码；命中黑名单的买单/卖单将被拒单并写入风控事件。" />
              </Label>
              <Input value={blacklist} onChange={(e) => setBlacklist(e.target.value)} />
            </div>
            <div className="space-y-2">
              <Label className="flex items-center gap-1">
                单笔最大金额（元）
                <InfoTip content="超过该金额的订单将被拒单（action=reject）；平台默认上限 50 万，可在规则集中进一步收紧。" />
              </Label>
              <Input value={maxAmount} onChange={(e) => setMaxAmount(e.target.value)} />
            </div>
          </div>
          <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
            创建规则集
          </Button>
          <p className="text-sm text-muted-foreground">
            内置规则类型还包括：max_position_pct（单票仓位上限）、max_count（持仓只数）、no_st（禁 ST）等，可通过 API 精细配置。
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>规则集列表</CardTitle>
        </CardHeader>
        <CardContent>
          {ruleSetsQuery.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>名称</TableHead>
                  <TableHead>规则数</TableHead>
                  <TableHead>创建时间</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(ruleSetsQuery.data?.list ?? []).map((rs) => (
                  <TableRow key={rs.id}>
                    <TableCell>{rs.name}</TableCell>
                    <TableCell>{rs.rules.length}</TableCell>
                    <TableCell>{fmtDateTime(rs.created_at)}</TableCell>
                    <TableCell className="text-right">
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => deleteMutation.mutate(rs.id)}
                        disabled={deleteMutation.isPending}
                      >
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

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            风控事件
            <InfoTip content="记录风控拒单、告警等事件；拒单时关联 order_id 与 portfolio_id，便于在交易中心排查。" />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>规则</TableHead>
                <TableHead>动作</TableHead>
                <TableHead>组合</TableHead>
                <TableHead>详情</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(eventsQuery.data?.list ?? []).map((ev) => (
                <TableRow key={ev.id}>
                  <TableCell>{fmtDateTime(ev.created_at)}</TableCell>
                  <TableCell>{ev.rule_type}</TableCell>
                  <TableCell>{ev.action}</TableCell>
                  <TableCell>{ev.portfolio_id ?? "—"}</TableCell>
                  <TableCell className="max-w-xs truncate">
                    {ev.detail?.reason ?? JSON.stringify(ev.detail ?? {})}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
