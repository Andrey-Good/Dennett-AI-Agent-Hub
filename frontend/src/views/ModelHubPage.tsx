import * as React from "react";
import { Play, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";
import { useModelStore } from "@/stores/modelStore";
import type { Model } from "@/types";

type Props = {
  onOpenDetails?: () => void;
};

type AgentStatus = "active" | "inactive";
type Activation = "trigger" | "time";

type Agent = {
  id: string;
  title: string;
  status: AgentStatus;
  activation: Activation;
  lastRun: string;
};

const QUICK_CHIPS = [
  "Архитектор агентов",
  "Создание записей в расписании",
  "Мозговой штурмовик",
  "Репертитор по английскому",
  "Заказ ужина",
  "Анализатор новостей",
  "Быстрая сводка по работе",
  "Подсчет калорий по фото",
  "Распределение обязаностей",
  "Поиск кода по 1 строчке",
  "Рассписание тренеровок",
];

const AGENTS: Agent[] = [
  {
    id: "a1",
    title: "Распределение задач по команде",
    status: "active",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a2",
    title: "Распределение задач по команде",
    status: "inactive",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a3",
    title: "Распределение задач по команде",
    status: "active",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a4",
    title: "Распределение задач по команде",
    status: "inactive",
    activation: "time",
    lastRun: "7 days ago",
  },
  {
    id: "a5",
    title: "Распределение задач по команде",
    status: "inactive",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a6",
    title: "Распределение задач по команде",
    status: "active",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a7",
    title: "Распределение задач по команде",
    status: "inactive",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a8",
    title: "Распределение задач по команде",
    status: "active",
    activation: "trigger",
    lastRun: "7 days ago",
  },
  {
    id: "a9",
    title: "Распределение задач по команде",
    status: "active",
    activation: "time",
    lastRun: "7 days ago",
  },
];

export function ModelHubPage({ onOpenDetails }: Props) {
  const { localModels, fetchLocalModels, searchModels, selectModel, isLoading } = useModelStore();

  const [chip, setChip] = React.useState(QUICK_CHIPS[0]);
  const [agentQuery, setAgentQuery] = React.useState("");
  const [modelQuery, setModelQuery] = React.useState("");

  React.useEffect(() => {
    // Left panel: local models.
    fetchLocalModels().catch(() => void 0);

    // If local list is empty, also load a small “popular” list to populate the panel.
    // (Does not change the overall architecture, only improves UX.)
    searchModels("").catch(() => void 0);
  }, [fetchLocalModels, searchModels]);

  const remoteModels = useModelStore((s) => s.models);

  const modelsForPanel = React.useMemo(() => {
    const base = localModels.length ? localModels : remoteModels;
    const q = modelQuery.trim().toLowerCase();
    if (!q) return base;
    return base.filter((m) => (m.name || "").toLowerCase().includes(q) || (m.id || "").toLowerCase().includes(q));
  }, [localModels, remoteModels, modelQuery]);

  const filteredAgents = React.useMemo(() => {
    const q = agentQuery.trim().toLowerCase();
    if (!q) return AGENTS;
    return AGENTS.filter((a) => a.title.toLowerCase().includes(q));
  }, [agentQuery]);

  const openDetails = (model: Model) => {
    selectModel(model);
    onOpenDetails?.();
  };

  return (
    <div className="relative h-full text-white">
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(1000px_circle_at_78%_20%,rgba(64,84,180,0.35),transparent_62%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(900px_circle_at_22%_78%,rgba(86,161,138,0.16),transparent_55%)]" />
      </div>

      <div className="grid h-full grid-cols-1 gap-6 overflow-hidden lg:grid-cols-[340px_1fr]">
        {/* Left models panel */}
        <Card className="h-full overflow-hidden p-0">
          <div className="flex h-full flex-col">
            <div className="p-4">
              <div className="text-[13px] font-semibold">Models</div>
              <div className="mt-3 relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--tp-faint))]" />
                <Input
                  value={modelQuery}
                  onChange={(e) => setModelQuery(e.target.value)}
                  placeholder="Search for models..."
                  className="h-10 rounded-2xl pl-9"
                />
              </div>
            </div>

            <ScrollArea className="flex-1 px-4 pb-4">
              <div className="space-y-3">
                {isLoading && modelsForPanel.length === 0 ? (
                  Array.from({ length: 6 }).map((_, idx) => <ModelPanelSkeleton key={idx} />)
                ) : modelsForPanel.length ? (
                  modelsForPanel.slice(0, 30).map((m) => (
                    <ModelPanelCard key={m.id} model={m} onClick={() => openDetails(m)} />
                  ))
                ) : (
                  <div className="rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] p-4 text-[11px] text-[hsl(var(--tp-muted))]">
                    No models yet. Import a local model or search on the Models page.
                  </div>
                )}
              </div>
            </ScrollArea>
          </div>
        </Card>

        {/* Right column */}
        <div className="flex h-full flex-col gap-6 overflow-hidden">
          {/* Quick chips row */}
          <Card className="p-4">
            <div className="flex flex-wrap gap-2">
              {QUICK_CHIPS.map((c) => {
                const active = chip === c;
                return (
                  <button
                    key={c}
                    type="button"
                    onClick={() => setChip(c)}
                    className={cn(
                      "rounded-lg border px-3 py-2 text-[11px] transition-colors",
                      active
                        ? "border-[hsl(var(--tp-blue))] bg-[hsl(var(--secondary))] text-white"
                        : "border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-pill))] text-white/80 hover:bg-[hsl(var(--secondary))]",
                    )}
                  >
                    {c}
                  </button>
                );
              })}
            </div>
          </Card>

          {/* Agents grid */}
          <Card className="flex-1 overflow-hidden p-0">
            <div className="flex h-full flex-col">
              <div className="p-4">
                <div className="relative w-full max-w-sm">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--tp-faint))]" />
                  <Input
                    value={agentQuery}
                    onChange={(e) => setAgentQuery(e.target.value)}
                    placeholder="Search for agents..."
                    className="h-11 rounded-2xl pl-9"
                  />
                </div>

                <div className="mt-3 text-[11px] text-[hsl(var(--tp-muted))]">
                  Selected: <span className="text-white/80">{chip}</span>
                </div>
              </div>

              <ScrollArea className="flex-1 px-4 pb-6">
                <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
                  {filteredAgents.map((agent) => (
                    <AgentCard key={agent.id} agent={agent} />
                  ))}
                </div>
              </ScrollArea>
            </div>
          </Card>
        </div>
      </div>
    </div>
  );
}

function ModelPanelCard({ model, onClick }: { model: Model; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "w-full rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))]/35 p-4 text-left",
        "shadow-[0px_1px_3px_rgba(0,0,0,0.10)] hover:bg-[hsl(var(--secondary))] transition-colors",
      )}
    >
      <div className="truncate text-[12px] font-semibold text-white/90">{model.name}</div>
      <div className="mt-1 text-[11px] text-[hsl(var(--tp-muted))]">
        {model.description || model.type}
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-[hsl(var(--tp-muted))]">
        <span className="truncate">Updated: {model.updated || "—"}</span>
        <span className="text-white/70">{model.downloads || "—"}</span>
      </div>
    </button>
  );
}

function ModelPanelSkeleton() {
  return (
    <div className="w-full rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))]/25 p-4">
      <div className="h-4 w-52 animate-pulse rounded bg-white/10" />
      <div className="mt-2 h-3 w-28 animate-pulse rounded bg-white/5" />
      <div className="mt-3 h-3 w-40 animate-pulse rounded bg-white/5" />
    </div>
  );
}

function AgentCard({ agent }: { agent: Agent }) {
  const isActive = agent.status === "active";

  return (
    <div
      className={cn(
        "rounded-2xl border border-[hsl(var(--tp-border))]/80 bg-[hsl(var(--tp-sidebar))]/25 p-5",
        "shadow-[0px_1px_3px_rgba(0,0,0,0.10)]",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="truncate text-[13px] font-semibold text-white/90">{agent.title}</div>
          <div className="mt-2 flex items-center gap-2 text-[11px] text-[hsl(var(--tp-muted))]">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                isActive ? "bg-emerald-500" : "bg-red-600",
              )}
            />
            <span className={cn(isActive ? "text-emerald-300" : "text-red-300")}
            >
              {isActive ? "Активен" : "Не активен"}
            </span>
          </div>
        </div>

        <Button
          type="button"
          variant="outline"
          className="h-8 rounded-xl px-3"
          title="(Placeholder) Run agent"
        >
          <Play className="mr-2 h-4 w-4" />
          Запустить
        </Button>
      </div>

      <div className="mt-4 space-y-1.5 text-[11px] text-[hsl(var(--tp-muted))]">
        <div className="flex items-center justify-between">
          <span>Активация:</span>
          <span className="text-white/80">
            {agent.activation === "trigger" ? "по тригеру" : "по времени"}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span>Последний запуск:</span>
          <span className="text-white/80">{agent.lastRun}</span>
        </div>
      </div>
    </div>
  );
}
