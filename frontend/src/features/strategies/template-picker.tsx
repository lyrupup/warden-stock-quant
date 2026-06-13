import { useQuery } from "@tanstack/react-query";
import { BookTemplate, Loader2 } from "lucide-react";
import {
  Button,
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  InfoTip,
} from "@/core/ui";
import type { TStrategyTemplate } from "@/types";
import { strategiesApi } from "./strategies-api";

type TTemplatePickerProps = {
  onPick: (tpl: TStrategyTemplate) => void;
};

export function TemplatePicker({ onPick }: TTemplatePickerProps) {
  const tplQuery = useQuery({
    queryKey: ["strategy-templates"],
    queryFn: strategiesApi.templates,
  });

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm" variant="outline">
          <BookTemplate className="mr-1 h-4 w-4" />
          模板库
        </Button>
      </DialogTrigger>
      <DialogContent className="max-h-[80vh] overflow-y-auto sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>策略模板库</DialogTitle>
          <DialogDescription>选择内置模板作为起点，可在编辑器中继续调整。</DialogDescription>
        </DialogHeader>
        {tplQuery.isLoading ? (
          <div className="flex justify-center py-6">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="min-w-0 space-y-3">
            {(tplQuery.data ?? []).map((tpl) => (
              <button
                key={tpl.id}
                type="button"
                className="block w-full min-w-0 rounded-lg border p-3 text-left transition hover:bg-muted/50"
                onClick={() => onPick(tpl)}
              >
                <div className="font-medium">{tpl.name}</div>
                <div className="mt-1 flex min-w-0 items-center gap-1.5">
                  <p className="min-w-0 flex-1 truncate text-sm text-muted-foreground">
                    {tpl.description}
                  </p>
                  <InfoTip content={tpl.description} align="right" bubbleClassName="w-72" />
                </div>
              </button>
            ))}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
