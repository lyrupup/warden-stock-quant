import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import { alertsApi } from "./alerts-api";

export function AlertsPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [webhookUrl, setWebhookUrl] = useState("https://example.com/webhook");

  const channelsQuery = useQuery({
    queryKey: ["alert-channels"],
    queryFn: alertsApi.listChannels,
  });

  const alertsQuery = useQuery({
    queryKey: ["alerts"],
    queryFn: () => alertsApi.listAlerts(1, 30),
  });

  const createMutation = useMutation({
    mutationFn: () =>
      alertsApi.createChannel({ type: "webhook", config: { url: webhookUrl } }),
    onSuccess: () => {
      toast.success("告警渠道已添加");
      void qc.invalidateQueries({ queryKey: ["alert-channels"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  const deleteMutation = useMutation({
    mutationFn: alertsApi.deleteChannel,
    onSuccess: () => {
      toast.success("已删除");
      void qc.invalidateQueries({ queryKey: ["alert-channels"] });
    },
    onError: (e) => toast.error(describeError(e)),
  });

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.alerts")}
        description="配置 Webhook/邮件等告警渠道，查看系统与任务触发的告警记录。"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            告警渠道
            <InfoTip content="任务失败、风控触发等事件会通过已启用渠道推送；Webhook 为最常用的集成方式。" />
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-end">
            <div className="flex-1 space-y-2">
              <Label>Webhook URL</Label>
              <Input value={webhookUrl} onChange={(e) => setWebhookUrl(e.target.value)} />
            </div>
            <Button onClick={() => createMutation.mutate()} disabled={createMutation.isPending}>
              添加 Webhook
            </Button>
          </div>
          {channelsQuery.isLoading ? (
            <Loader2 className="h-6 w-6 animate-spin" />
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>类型</TableHead>
                  <TableHead>配置</TableHead>
                  <TableHead className="text-right">操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(channelsQuery.data ?? []).map((c) => (
                  <TableRow key={c.id}>
                    <TableCell>{c.type}</TableCell>
                    <TableCell className="max-w-md truncate">{JSON.stringify(c.config)}</TableCell>
                    <TableCell className="text-right">
                      <Button size="sm" variant="ghost" onClick={() => deleteMutation.mutate(c.id)}>
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
          <CardTitle>告警记录</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>时间</TableHead>
                <TableHead>级别</TableHead>
                <TableHead>标题</TableHead>
                <TableHead>已发送</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(alertsQuery.data?.list ?? []).map((a) => (
                <TableRow key={a.id}>
                  <TableCell>{fmtDateTime(a.created_at)}</TableCell>
                  <TableCell>{a.level}</TableCell>
                  <TableCell>{a.title}</TableCell>
                  <TableCell>{a.sent ? "是" : "否"}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
