import { useTranslation } from "react-i18next";
import { PageHeader } from "@/core/ui";
import { ProfileCard } from "./profile-card";
import { QuotaCard } from "./quota-card";
import { ApiKeysCard } from "./api-keys-card";

export function AccountPage() {
  const { t } = useTranslation();
  return (
    <div className="space-y-6">
      <PageHeader title={t("nav.account")} description="个人设置、API Key 与配额套餐管理。" />
      <div className="grid gap-6 lg:grid-cols-2">
        <ProfileCard />
        <QuotaCard />
      </div>
      <ApiKeysCard />
    </div>
  );
}
