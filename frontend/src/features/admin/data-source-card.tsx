import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Server } from "lucide-react";
import { describeError } from "@/core/http";
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Input,
  Label,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  toast,
} from "@/core/ui";
import { adminApi } from "./admin-api";

export function DataSourceCard() {
  const qc = useQueryClient();
  const [baseUrl, setBaseUrl] = useState("http://localhost:8080");
  const [secretId, setSecretId] = useState("");
  const [secretKey, setSecretKey] = useState("");
  const [name, setName] = useState("default");

  const listQuery = useQuery({
    queryKey: ["admin", "data-source"],
    queryFn: adminApi.listDataSources,
  });

  const createMutation = useMutation({
    mutationFn: adminApi.createDataSource,
    onSuccess: () => {
      toast.success("数据源凭证已保存（secretKey 不再回显）");
      setSecretKey("");
      void qc.invalidateQueries({ queryKey: ["admin", "data-source"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Server className="h-5 w-5" />
          warden-stock-data 数据源
        </CardTitle>
        <CardDescription>
          配置 HMAC 凭证（secretKey 仅写入一次，服务端加密存储）
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <Label htmlFor="ds-name">名称</Label>
            <Input id="ds-name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds-url">Base URL</Label>
            <Input
              id="ds-url"
              value={baseUrl}
              onChange={(e) => setBaseUrl(e.target.value)}
              placeholder="http://localhost:8080"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds-sid">Secret ID</Label>
            <Input id="ds-sid" value={secretId} onChange={(e) => setSecretId(e.target.value)} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="ds-skey">Secret Key</Label>
            <Input
              id="ds-skey"
              type="password"
              value={secretKey}
              onChange={(e) => setSecretKey(e.target.value)}
            />
          </div>
        </div>
        <Button
          disabled={createMutation.isPending || !secretId || !secretKey}
          onClick={() =>
            createMutation.mutate({
              name,
              base_url: baseUrl,
              secret_id: secretId,
              secret_key: secretKey,
            })
          }
        >
          {createMutation.isPending ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
          保存凭证
        </Button>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>ID</TableHead>
              <TableHead>名称</TableHead>
              <TableHead>Base URL</TableHead>
              <TableHead>Secret ID</TableHead>
              <TableHead>状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {(listQuery.data ?? []).map((row) => (
              <TableRow key={row.id}>
                <TableCell>{row.id}</TableCell>
                <TableCell>{row.name ?? "—"}</TableCell>
                <TableCell className="max-w-[200px] truncate">{row.base_url}</TableCell>
                <TableCell className="font-mono text-xs">{row.secret_id}</TableCell>
                <TableCell>{row.enabled ? "启用" : "禁用"}</TableCell>
              </TableRow>
            ))}
            {!listQuery.data?.length && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  暂无凭证
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
