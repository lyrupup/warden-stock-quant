import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Copy, KeyRound, Loader2, Plus, Trash2 } from "lucide-react";
import { fmtDateTime } from "@/core/lib";
import { describeError } from "@/core/http";
import { EApiKeyScope } from "@/types";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
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
import { accountApi, normalizeApiKeys } from "./account-api";

const ALL_SCOPES = [
  EApiKeyScope.Read,
  EApiKeyScope.Backtest,
  EApiKeyScope.Factor,
  EApiKeyScope.Trade,
];

export function ApiKeysCard() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [name, setName] = useState("");
  const [scopes, setScopes] = useState<string[]>([EApiKeyScope.Read]);
  const [plaintext, setPlaintext] = useState<string | null>(null);

  const listQuery = useQuery({
    queryKey: ["api-keys"],
    queryFn: accountApi.listApiKeys,
  });
  const keys = normalizeApiKeys(listQuery.data);

  const createMutation = useMutation({
    mutationFn: accountApi.createApiKey,
    onSuccess: (data) => {
      setCreateOpen(false);
      setName("");
      setScopes([EApiKeyScope.Read]);
      setPlaintext(data.key);
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const revokeMutation = useMutation({
    mutationFn: accountApi.revokeApiKey,
    onSuccess: () => {
      toast.success(t("common.confirm"));
      void qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
    onError: (err) => toast.error(describeError(err)),
  });

  const toggleScope = (scope: string) =>
    setScopes((prev) => (prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]));

  const onCopy = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(t("common.copied"));
    } catch {
      toast.error("复制失败，请手动选择");
    }
  };

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="flex items-center gap-2">
            <KeyRound className="h-4 w-4" />
            {t("account.apiKeys")}
          </CardTitle>
          <CardDescription>程序化访问凭证，明文仅创建时展示一次。</CardDescription>
        </div>
        <Button size="sm" onClick={() => setCreateOpen(true)}>
          <Plus className="h-4 w-4" />
          {t("account.createKey")}
        </Button>
      </CardHeader>
      <CardContent>
        {listQuery.isLoading ? (
          <div className="flex items-center justify-center py-10 text-muted-foreground">
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            {t("common.loading")}
          </div>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("account.keyName")}</TableHead>
                <TableHead>Prefix</TableHead>
                <TableHead>{t("account.scopes")}</TableHead>
                <TableHead>{t("common.status")}</TableHead>
                <TableHead>{t("common.createdAt")}</TableHead>
                <TableHead className="text-right">{t("common.actions")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {keys.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="h-20 text-center text-muted-foreground">
                    {t("common.empty")}
                  </TableCell>
                </TableRow>
              ) : (
                keys.map((k) => (
                  <TableRow key={k.id}>
                    <TableCell className="font-medium">{k.name}</TableCell>
                    <TableCell className="font-mono text-xs">{k.prefix ?? "-"}</TableCell>
                    <TableCell>
                      <div className="flex flex-wrap gap-1">
                        {(k.scopes ?? []).map((s) => (
                          <Badge key={String(s)} variant="secondary">
                            {String(s)}
                          </Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={k.status === "revoked" ? "destructive" : "success"}>
                        {k.status ?? "active"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fmtDateTime(k.created_at)}
                    </TableCell>
                    <TableCell className="text-right">
                      <Button
                        variant="ghost"
                        size="icon"
                        className="text-destructive"
                        disabled={revokeMutation.isPending}
                        onClick={() => {
                          if (window.confirm(t("account.revokeConfirm"))) revokeMutation.mutate(k.id);
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        )}
      </CardContent>

      {/* 创建对话框 */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("account.createKey")}</DialogTitle>
            <DialogDescription>选择权限范围，创建后将一次性展示明文 Key。</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="key-name">{t("account.keyName")}</Label>
              <Input
                id="key-name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="my-research-key"
              />
            </div>
            <div className="space-y-2">
              <Label>{t("account.scopes")}</Label>
              <div className="flex flex-wrap gap-2">
                {ALL_SCOPES.map((scope) => (
                  <button
                    type="button"
                    key={scope}
                    onClick={() => toggleScope(scope)}
                    className={
                      "rounded-md border px-3 py-1 text-sm transition-colors " +
                      (scopes.includes(scope)
                        ? "border-primary bg-primary/10 text-primary"
                        : "text-muted-foreground hover:bg-accent")
                    }
                  >
                    {scope}
                  </button>
                ))}
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{t("common.cancel")}</Button>
            </DialogClose>
            <Button
              disabled={!name || scopes.length === 0 || createMutation.isPending}
              onClick={() => createMutation.mutate({ name, scopes })}
            >
              {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
              {t("common.create")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* 明文一次性展示对话框 */}
      <Dialog open={!!plaintext} onOpenChange={(o) => !o && setPlaintext(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("account.keyPlaintextTitle")}</DialogTitle>
            <DialogDescription className="text-destructive">
              {t("account.keyPlaintextHint")}
            </DialogDescription>
          </DialogHeader>
          <div className="flex items-center gap-2 rounded-md border bg-muted/50 p-3">
            <code className="flex-1 break-all font-mono text-sm">{plaintext}</code>
            <Button
              variant="outline"
              size="icon"
              onClick={() => plaintext && onCopy(plaintext)}
              aria-label={t("common.copy")}
            >
              <Copy className="h-4 w-4" />
            </Button>
          </div>
          <DialogFooter>
            <Button onClick={() => setPlaintext(null)}>{t("common.confirm")}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Card>
  );
}
