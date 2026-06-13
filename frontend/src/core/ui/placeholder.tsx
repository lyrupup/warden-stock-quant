import { Construction } from "lucide-react";
import { useTranslation } from "react-i18next";
import { PageHeader } from "./page-header";
import { Card, CardContent } from "./card";

/** 通用「开发中」占位页：标题 + 提示，保证导航可点、骨架完整 */
export function PlaceholderPage({ titleKey, title }: { titleKey?: string; title?: string }) {
  const { t } = useTranslation();
  const heading = title ?? (titleKey ? t(titleKey) : "");
  return (
    <div className="space-y-6">
      <PageHeader title={heading} />
      <Card>
        <CardContent className="flex flex-col items-center justify-center gap-3 py-20 text-center">
          <Construction className="h-10 w-10 text-muted-foreground" />
          <p className="text-lg font-medium">{t("common.inDevelopment")}</p>
          <p className="max-w-sm text-sm text-muted-foreground">{t("common.inDevelopmentHint")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
