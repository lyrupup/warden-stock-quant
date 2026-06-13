import { useTranslation } from "react-i18next";
import { PageHeader } from "@/core/ui";
import { DatasetStatusCard, DatasetSyncCard } from "./dataset-cards";

export function DatasetsPage() {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.datasets")}
        description="对接 warden-stock-data，管理本地行情数据集与同步作业。"
      />
      <div className="grid gap-6 lg:grid-cols-2">
        <DatasetStatusCard />
        <DatasetSyncCard />
      </div>
    </div>
  );
}
