import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, Pencil, Plus, Trash2 } from "lucide-react";
import { describeError } from "@/core/http";
import {
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  toast,
} from "@/core/ui";
import type { TStrategy } from "@/types";
import { strategiesApi } from "./strategies-api";
import { TemplatePicker } from "./template-picker";

type TStrategyListProps = {
  onCreateBlank: () => void;
};

export function StrategyList({ onCreateBlank }: TStrategyListProps) {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const listQuery = useQuery({
    queryKey: ["strategies"],
    queryFn: () => strategiesApi.list(1, 50),
  });

  const deleteMutation = useMutation({
    mutationFn: strategiesApi.remove,
    onSuccess: () => {
      toast.success("策略已删除");
      void qc.invalidateQueries({ queryKey: ["strategies"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const items = listQuery.data?.list ?? [];

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-4">
        <CardTitle>我的策略</CardTitle>
        <div className="flex gap-2">
          <TemplatePicker
            onPick={(tpl) => {
              navigate("/strategies/new", { state: { template: tpl } });
            }}
          />
          <Button size="sm" onClick={onCreateBlank}>
            <Plus className="mr-1 h-4 w-4" />
            新建策略
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        {listQuery.isLoading ? (
          <div className="flex justify-center py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : items.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            暂无策略，可从模板库一键创建或新建空白策略。
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>名称</TableHead>
                <TableHead>类型</TableHead>
                <TableHead>版本</TableHead>
                <TableHead>更新时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((s: TStrategy) => (
                <TableRow key={s.id}>
                  <TableCell>
                    <Link
                      to={`/strategies/${s.id}`}
                      className="font-medium text-primary hover:underline"
                    >
                      {s.name}
                    </Link>
                  </TableCell>
                  <TableCell>{s.type === "config" ? "配置式" : "代码式"}</TableCell>
                  <TableCell>v{s.latest_version}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {s.updated_at ? new Date(s.updated_at).toLocaleString() : "—"}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="icon" asChild>
                      <Link to={`/strategies/${s.id}`}>
                        <Pencil className="h-4 w-4" />
                      </Link>
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => {
                        if (confirm(`确认删除策略「${s.name}」？`)) {
                          deleteMutation.mutate(s.id);
                        }
                      }}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
