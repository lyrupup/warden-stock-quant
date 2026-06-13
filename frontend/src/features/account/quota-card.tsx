import { useTranslation } from "react-i18next";
import { useAuth } from "@/core/auth";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/core/ui";

/** 配额套餐展示占位：后端 quota 结构稳定后再细化各项用量进度条 */
export function QuotaCard() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const quota = (user?.quota ?? {}) as Record<string, unknown>;
  const entries = Object.entries(quota);

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("account.quota")}</CardTitle>
        <CardDescription>当前套餐：{user?.plan ?? "free"}</CardDescription>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted-foreground">
            {t("common.inDevelopmentHint")}
          </p>
        ) : (
          <div className="space-y-3">
            {entries.map(([key, value]) => (
              <div key={key} className="flex items-center justify-between text-sm">
                <span className="text-muted-foreground">{key}</span>
                <span className="font-medium">{String(value)}</span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
