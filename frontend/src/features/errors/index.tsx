import { type ReactNode } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ShieldX, FileQuestion } from "lucide-react";
import { Button } from "@/core/ui";

function ErrorScreen({
  icon,
  code,
  title,
  hint,
}: {
  icon: ReactNode;
  code: string;
  title: string;
  hint?: string;
}) {
  const { t } = useTranslation();
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-4 text-center">
      {icon}
      <div className="text-5xl font-bold text-muted-foreground">{code}</div>
      <h1 className="text-xl font-semibold">{title}</h1>
      {hint ? <p className="max-w-sm text-sm text-muted-foreground">{hint}</p> : null}
      <Button asChild>
        <Link to="/">{t("error.backHome")}</Link>
      </Button>
    </div>
  );
}

export function NotFoundPage() {
  const { t } = useTranslation();
  return (
    <ErrorScreen
      icon={<FileQuestion className="h-12 w-12 text-muted-foreground" />}
      code="404"
      title={t("error.notFound")}
    />
  );
}

export function ForbiddenPage() {
  const { t } = useTranslation();
  return (
    <ErrorScreen
      icon={<ShieldX className="h-12 w-12 text-destructive" />}
      code="403"
      title={t("error.forbidden")}
      hint={t("error.forbiddenHint")}
    />
  );
}
