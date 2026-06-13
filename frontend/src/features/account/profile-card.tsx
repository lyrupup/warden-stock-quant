import { useTranslation } from "react-i18next";
import { useAuth } from "@/core/auth";
import { Badge, Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/core/ui";

export function ProfileCard() {
  const { t } = useTranslation();
  const { user } = useAuth();

  const rows: { label: string; value: string }[] = [
    { label: t("auth.email"), value: user?.email ?? "-" },
    { label: t("auth.username"), value: user?.username ?? "-" },
    { label: "ID", value: user?.id != null ? String(user.id) : "-" },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("account.profile")}</CardTitle>
        <CardDescription>账户基础信息（改密等编辑能力后续接入）。</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {rows.map((r) => (
          <div key={r.label} className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">{r.label}</span>
            <span className="font-medium">{r.value}</span>
          </div>
        ))}
        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">角色 / 套餐</span>
          <span className="flex items-center gap-2">
            <Badge variant="secondary">{user?.role ?? "user"}</Badge>
            <Badge variant="outline">{user?.plan ?? "free"}</Badge>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
