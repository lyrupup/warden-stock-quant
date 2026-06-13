import { useTranslation } from "react-i18next";
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { Button, PageHeader } from "@/core/ui";
import { OptimizationCreate } from "./optimization-create";
import { OptimizationDetail } from "./optimization-detail";
import { OptimizationList } from "./optimization-list";

export function OptimizationsPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id?: string }>();
  const navigate = useNavigate();

  const isNew = id === "new";
  const isDetail = !!id && !isNew;
  const optimizationId = isDetail ? Number(id) : undefined;

  return (
    <div className="space-y-6">
      <PageHeader
        title={t("nav.optimizations")}
        description="对策略参数做网格/随机搜索，批量回测并按夏普等指标排序，支持样本内外拆分与过拟合诊断。"
        actions={
          id ? (
            <Button variant="outline" size="sm" onClick={() => navigate("/optimizations")}>
              <ArrowLeft className="mr-1 h-4 w-4" />
              返回列表
            </Button>
          ) : undefined
        }
      />

      {isNew ? (
        <OptimizationCreate />
      ) : isDetail && optimizationId ? (
        <OptimizationDetail optimizationId={optimizationId} />
      ) : (
        <OptimizationList onCreate={() => navigate("/optimizations/new")} />
      )}
    </div>
  );
}
