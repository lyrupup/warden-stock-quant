import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button, PageHeader } from "@/core/ui";
import type { TStrategyTemplate } from "@/types";
import { StrategyEditor } from "./strategy-editor";
import { StrategyList } from "./strategy-list";

export function StrategiesPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const template = (location.state as { template?: TStrategyTemplate } | null)?.template;

  const isEditor = !!id;
  const isNew = id === "new";
  const strategyId = isNew || !id ? undefined : Number(id);

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.strategies")}
        description="配置式策略管理：信号积木、股票池、版本化与模板库。"
        actions={
          isEditor ? (
            <Button variant="outline" size="sm" onClick={() => navigate("/strategies")}>
              <ArrowLeft className="mr-1 h-4 w-4" />
              返回列表
            </Button>
          ) : undefined
        }
      />

      {isEditor ? (
        <StrategyEditor strategyId={strategyId} template={template} />
      ) : (
        <StrategyList onCreateBlank={() => navigate("/strategies/new")} />
      )}
    </div>
  );
}
