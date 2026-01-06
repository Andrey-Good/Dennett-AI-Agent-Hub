import * as React from "react";
import {
  ArrowUpRight,
  Cpu,
  Download,
  ExternalLink,
  Info,
  Tag,
  X,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Progress } from "@/components/ui/progress";
import { api } from "@/api/client";
import { useModelStore } from "@/stores/modelStore";

interface ModelDetailsPanelProps {
  open: boolean;
  onClose: () => void;
}

export function ModelDetailsPanel({ open, onClose }: ModelDetailsPanelProps) {
  const { selectedModel } = useModelStore();
  const [details, setDetails] = React.useState<any | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    if (!open || !selectedModel) return;

    const repoId = selectedModel.id;
    if (!repoId || typeof repoId !== "string" || !repoId.includes("/")) {
      setDetails(null);
      return;
    }

    const [author, modelName] = repoId.split("/");
    setLoading(true);
    setError(null);

    api.hub
      .getDetails(author, modelName)
      .then((data) => {
        setDetails(data);
      })
      .catch((err: unknown) => {
        console.error("Failed to load model details", err);
        setError(
          err instanceof Error ? err.message : "Не удалось загрузить описание модели.",
        );
      })
      .finally(() => setLoading(false));
  }, [open, selectedModel]);

  if (!open || !selectedModel) return null;

  const repoUrl =
    (details as any)?.url ??
    (details as any)?.cardData?.widget?.repository ??
    (selectedModel.id ? `https://huggingface.co/${selectedModel.id}` : null);

  const license =
    (details as any)?.license ??
    (details as any)?.cardData?.license ??
    (details as any)?.config?.license ??
    "Unknown";

  const tags: string[] =
    (details as any)?.tags ??
    (details as any)?.cardData?.tags ??
    (details as any)?.cardData?.keywords ??
    [];

  const description: string =
    (details as any)?.cardData?.description ??
    (details as any)?.description ??
    selectedModel.description ??
    "No description yet. Connect the Hugging Face API to see a full model card here.";

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-[420px] border-l border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] shadow-[0_0_70px_rgba(0,0,0,0.75)]">
      <div className="flex h-14 items-center justify-between border-b border-[hsl(var(--tp-border))] px-4">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--tp-muted))]">
            Model
          </div>
          <div className="mt-0.5 truncate text-[12px] font-semibold text-white/90">
            {selectedModel.name}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {repoUrl && (
            <Button
              asChild
              variant="outline"
              size="icon"
              className="h-9 w-9 rounded-xl"
            >
              <a href={repoUrl} target="_blank" rel="noreferrer" aria-label="Open on Hugging Face">
                <ExternalLink className="h-4 w-4" />
              </a>
            </Button>
          )}
          <Button
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-xl"
            onClick={onClose}
            aria-label="Close"
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
      </div>

      <ScrollArea className="h-[calc(100%-3.5rem)]">
        <div className="space-y-4 px-4 py-4 pb-8 text-white">
          {error && (
            <div className="rounded-2xl border border-[#5a3d14] bg-[#2a1c09] px-3 py-2 text-[11px] text-[#f4d7a6]">
              {error}
            </div>
          )}

          <Card>
            <div className="flex items-start justify-between gap-3 border-b border-[hsl(var(--tp-border))] px-4 py-3">
              <div>
                <div className="text-[12px] font-semibold">Overview</div>
                <div className="mt-0.5 text-[11px] text-[hsl(var(--tp-muted))]">
                  {loading ? "Loading model card…" : "Hugging Face model card summary"}
                </div>
              </div>
              <Info className="h-4 w-4 text-[hsl(var(--tp-faint))]" />
            </div>

            <div className="space-y-3 px-4 py-4 text-[11px] text-white/90">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-[hsl(var(--tp-sidebar))] text-white/80">
                  <Cpu className="mr-1 h-3 w-3" />
                  {selectedModel.type || "text-generation"}
                </Badge>
                <Badge className="bg-[hsl(var(--tp-sidebar))] text-white/80">
                  <Download className="mr-1 h-3 w-3" />
                  {selectedModel.downloads || "—"} downloads
                </Badge>
                <Badge className="bg-[hsl(var(--tp-sidebar))] text-white/80">
                  License: {license}
                </Badge>
              </div>

              <div className="rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--background))] p-3">
                <p className="whitespace-pre-line leading-relaxed text-white/85">{description}</p>
              </div>

              <div className="space-y-1">
                <div className="flex items-center justify-between text-[11px] text-[hsl(var(--tp-muted))]">
                  <span>Quality</span>
                  <span>Est. 86%</span>
                </div>
                <Progress value={86} />
              </div>
            </div>
          </Card>

          <Card>
            <div className="flex items-start justify-between gap-3 border-b border-[hsl(var(--tp-border))] px-4 py-3">
              <div>
                <div className="text-[12px] font-semibold">Tags & tasks</div>
                <div className="mt-0.5 text-[11px] text-[hsl(var(--tp-muted))]">
                  What this model is most suitable for
                </div>
              </div>
              <Tag className="h-4 w-4 text-[hsl(var(--tp-faint))]" />
            </div>

            <div className="px-4 py-4">
              {tags && tags.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {tags.slice(0, 18).map((tag: string) => (
                    <Badge
                      key={tag}
                      variant="outline"
                      className="bg-[hsl(var(--tp-sidebar))] text-white/80"
                    >
                      {tag}
                    </Badge>
                  ))}
                </div>
              ) : (
                <p className="text-[11px] text-[hsl(var(--tp-muted))]">
                  No tags yet — once the backend returns a full model card, they will appear here.
                </p>
              )}
            </div>
          </Card>

          <Card>
            <div className="flex items-start justify-between gap-3 border-b border-[hsl(var(--tp-border))] px-4 py-3">
              <div>
                <div className="text-[12px] font-semibold">Quick actions</div>
                <div className="mt-0.5 text-[11px] text-[hsl(var(--tp-muted))]">
                  Add the model to hub or start a test chat.
                </div>
              </div>
              <ArrowUpRight className="h-4 w-4 text-[hsl(var(--tp-faint))]" />
            </div>

            <div className="flex flex-col gap-2 px-4 py-4 text-[11px]">
              <Button className="h-9 justify-start rounded-xl">Add to local model hub</Button>
              <Button
                variant="outline"
                className="h-9 justify-start rounded-xl"
              >
                Start chat with this model
              </Button>
            </div>
          </Card>
        </div>
      </ScrollArea>
    </div>
  );
}
