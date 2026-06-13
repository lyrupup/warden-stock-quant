import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button, PageHeader } from "@/core/ui";
import { BacktestCreate } from "./backtest-create";
import { BacktestDetail } from "./backtest-detail";
import { BacktestList } from "./backtest-list";

export function BacktestsPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const isNew = id === "new";
  const isDetail = !!id && !isNew;
  const backtestId = isDetail ? Number(id) : undefined;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.backtests")}
        description="基于本地行情对策略版本做日频回测：A 股 T+1/涨跌停/成本建模，输出净值与绩效。"
        actions={
          id ? (
            <Button variant="outline" size="sm" onClick={() => navigate("/backtests")}>
              <ArrowLeft className="mr-1 h-4 w-4" />
              返回列表
            </Button>
          ) : undefined
        }
      />

      {isNew ? (
        <BacktestCreate />
      ) : isDetail && backtestId ? (
        <BacktestDetail backtestId={backtestId} />
      ) : (
        <BacktestList onCreate={() => navigate("/backtests/new")} />
      )}
    </div>
  );
}
