import { PageHeader } from "@/core/ui";
import { DataSourceCard } from "./data-source-card";

export function AdminPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="运营管理" description="用户、数据源凭证、套餐与系统监控（M1/M2 骨架）。" />
      <DataSourceCard />
    </div>
  );
}
