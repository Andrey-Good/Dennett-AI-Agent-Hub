import * as React from "react";
import {
  Clock,
  Folder,
  List,
  MoreHorizontal,
  Plus,
  SquareKanban,
  Table,
} from "lucide-react";

import { cn } from "@/lib/utils";
import { useModelStore } from "@/stores/modelStore";

type View = "kanban" | "list" | "timeline" | "table";

type Props = {
  onOpenDetails?: () => void;
};

const columns = [
  { id: "todo", label: "To Do", accent: "muted" as const },
  { id: "inprogress", label: "In Progress", accent: "blue" as const },
  { id: "done", label: "Done", accent: "muted" as const },
];

export function ModelHubPage({ onOpenDetails }: Props) {
  const [view, setView] = React.useState<View>("kanban");

  const {
    localModels,
    loadingLocal,
    fetchLocalModels,
    selectModel,
  } = useModelStore();

  React.useEffect(() => {
    fetchLocalModels();
  }, [fetchLocalModels]);

  const todoCards = [
    {
      title: "Add first HuggingFace model",
      priority: "Medium",
      tag: "Hub",
      meta: "Search and pin models you use most.",
      progress: 35,
    },
    {
      title: "Create default inference preset",
      priority: "High",
      tag: "API",
      meta: "Tune generation params for your workflow.",
      progress: 62,
    },
  ];

  const doneCards = [
    {
      title: "Dennett hub ready",
      priority: "Medium",
      tag: "Core",
      meta: "UI + API wiring is configured.",
      progress: 100,
    },
  ];

  return (
    <div className="h-full text-white">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="flex items-center gap-2 text-[11px] text-[hsl(var(--tp-muted))]">
            <span>Project</span>
            <span className="opacity-60">/</span>
            <span className="text-white/80">Model Hub</span>
          </div>

          <div className="mt-3 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[#262e50]">
              <Folder className="h-5 w-5 text-[#5563a2]" />
            </div>
            <h1 className="text-[30px] font-semibold tracking-tight">Model Hub</h1>
          </div>
        </div>

        <div className="flex items-center gap-2 pt-2">
          <ViewTabs view={view} onChange={setView} />
        </div>
      </div>

      {/* Board */}
      <div className="mt-6 grid h-[calc(100%-112px)] grid-cols-1 gap-4 overflow-hidden lg:grid-cols-3">
        {columns.map((col) => (
          <div key={col.id} className="flex h-full flex-col">
            <div className="mb-3 flex items-center gap-2 px-1">
              <span
                className={cn(
                  "h-4 w-[3px] rounded-full",
                  col.accent === "blue" ? "bg-[hsl(var(--tp-blue))]" : "bg-[hsl(var(--tp-border))]",
                )}
              />
              <div className="text-[12px] font-semibold text-white/90">{col.label}</div>
            </div>

            <div className="flex-1 overflow-auto pr-2">
              <div className="space-y-3">
                {col.id === "todo" &&
                  todoCards.map((c) => <KanbanCard key={c.title} {...c} />)}

                {col.id === "inprogress" && (
                  <>
                    {loadingLocal ? (
                      <KanbanCard
                        title="Loading local models…"
                        priority="Medium"
                        tag="Local"
                        meta="Fetching from backend"
                        progress={45}
                        skeleton
                      />
                    ) : localModels.length === 0 ? (
                      <EmptyState />
                    ) : (
                      localModels.slice(0, 12).map((m) => (
                        <KanbanCard
                          key={m.id}
                          title={m.name}
                          priority="Medium"
                          tag={m.type.toUpperCase()}
                          meta={m.description || "Local model"}
                          progress={75}
                          onClick={() => {
                            selectModel(m);
                            onOpenDetails?.();
                          }}
                        />
                      ))
                    )}
                  </>
                )}

                {col.id === "done" && doneCards.map((c) => <KanbanCard key={c.title} {...c} />)}

                <button
                  type="button"
                  className="mt-2 flex w-full items-center justify-center gap-2 rounded-2xl border border-dashed border-[hsl(var(--tp-border))] bg-transparent py-3 text-[12px] font-semibold text-[hsl(var(--tp-muted))] hover:bg-[hsl(var(--card))] hover:text-white"
                >
                  <Plus className="h-4 w-4" />
                  Add New
                </button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ViewTabs({ view, onChange }: { view: View; onChange: (v: View) => void }) {
  const tabs: { id: View; label: string; icon: React.ComponentType<any> }[] = [
    { id: "kanban", label: "Kanban", icon: SquareKanban },
    { id: "list", label: "List", icon: List },
    { id: "timeline", label: "Timeline", icon: Clock },
    { id: "table", label: "Table", icon: Table },
  ];

  return (
    <div className="inline-flex items-center gap-1 rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] p-1">
      {tabs.map(({ id, label, icon: Icon }) => {
        const active = view === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onChange(id)}
            className={cn(
              "inline-flex items-center gap-2 rounded-xl px-3 py-2 text-[12px] font-semibold transition-colors",
              active
                ? "bg-[hsl(var(--card))] text-white"
                : "text-[hsl(var(--tp-muted))] hover:text-white",
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </button>
        );
      })}
    </div>
  );
}

type KanbanCardProps = {
  title: string;
  priority: "Low" | "Medium" | "High";
  tag: string;
  meta: string;
  progress: number;
  skeleton?: boolean;
  onClick?: () => void;
};

function KanbanCard({ title, priority, tag, meta, progress, skeleton, onClick }: KanbanCardProps) {
  return (
    <div
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      onClick={onClick}
      onKeyDown={(e) => {
        if (!onClick) return;
        if (e.key === "Enter" || e.key === " ") onClick();
      }}
      className={cn(
        "rounded-[18px] border border-[hsl(var(--tp-border))] bg-[hsl(var(--card))] p-4 shadow-[0_18px_50px_rgba(0,0,0,0.55)]",
        onClick && "cursor-pointer hover:bg-[hsl(var(--secondary))]",
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <PriorityPill level={priority} />
          <TagPill text={tag} />
        </div>

        <button
          type="button"
          className="text-[hsl(var(--tp-faint))] hover:text-white"
          onClick={(e) => e.stopPropagation()}
          aria-label="More"
        >
          <MoreHorizontal className="h-4 w-4" />
        </button>
      </div>

      <div className={cn("mt-3 text-[13px] font-semibold", skeleton && "opacity-70")}>{title}</div>

      <div className="mt-2 text-[11px] text-[hsl(var(--tp-muted))] line-clamp-2">{meta}</div>

      <div className="mt-4 flex items-center justify-between">
        <SegmentBar value={progress} />
        <div className="text-[11px] text-[hsl(var(--tp-muted))]">
          {Math.round((progress / 100) * 20)} / 20
        </div>
      </div>
    </div>
  );
}

function SegmentBar({ value }: { value: number }) {
  const segments = 20;
  const filled = Math.round((value / 100) * segments);
  return (
    <div className="flex items-center gap-0.5">
      {Array.from({ length: segments }).map((_, i) => (
        <div
          key={i}
          className={cn(
            "h-2 w-1 rounded-sm",
            i < filled ? "bg-[#4054b4]" : "bg-[hsl(var(--tp-sidebar))]",
          )}
        />
      ))}
    </div>
  );
}

function PriorityPill({ level }: { level: "Low" | "Medium" | "High" }) {
  const dot = level === "High" ? "bg-[#b94a4a]" : level === "Medium" ? "bg-[#b9a24a]" : "bg-[#56a18a]";
  return (
    <span className="inline-flex items-center gap-2 rounded-full border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] px-2 py-1 text-[10px] font-semibold text-white/80">
      <span className={cn("h-1.5 w-1.5 rounded-full", dot)} />
      {level}
    </span>
  );
}

function TagPill({ text }: { text: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] px-2 py-1 text-[10px] font-semibold text-[hsl(var(--tp-muted))]">
      {text}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="rounded-[18px] border border-dashed border-[hsl(var(--tp-border))] bg-transparent p-5 text-center">
      <div className="text-[12px] font-semibold text-white/90">No local models yet</div>
      <div className="mt-1 text-[11px] text-[hsl(var(--tp-muted))]">
        Add a model via Search and it will appear here.
      </div>
    </div>
  );
}
