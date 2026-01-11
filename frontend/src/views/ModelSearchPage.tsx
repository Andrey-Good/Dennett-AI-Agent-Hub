import * as React from "react";
import {
  ArrowRightLeft,
  Box,
  ChevronDown,
  Film,
  Filter,
  Image,
  Languages,
  Loader2,
  Search,
  Shuffle,
  Type,
  Upload,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import { cn } from "@/lib/utils";
import { useModelStore } from "@/stores/modelStore";
import type { FilterState, Model } from "@/types";

interface ModelSearchPageProps {
  onOpenDetails: () => void;
}

type FiltersTab = "main" | "tasks" | "languages" | "license";

type TaskItem = {
  id: string;
  label: string;
  icon: React.ElementType;
  extra?: string;
};

const TASKS: TaskItem[] = [
  { id: "text-generation", label: "Text Generation", icon: Type },
  { id: "text-to-text", label: "Text-to-text", icon: ArrowRightLeft },
  { id: "any-to-any", label: "Any-to-any", icon: Shuffle },
  { id: "image-to-text", label: "Image-to-text", icon: Image },
  { id: "image-text-to-text", label: "Image-text-to-text", icon: Image },
  { id: "3d-to-text", label: "3D-to-Text", icon: Box },
  { id: "translation", label: "Translation", icon: Languages },
  { id: "text-to-video", label: "Text-to-Video", icon: Film, extra: "+42" },
];

const LANGUAGES = ["English", "Русский", "Deutsch", "Español", "Français"];
const LICENSES = ["apache-2.0", "mit", "llama2", "openrail", "proprietary"];

const WEIGHT_TICKS: Array<{ v: number; label: string }> = [
  { v: 0.1, label: "0.1" },
  { v: 0.5, label: "0.5" },
  { v: 1, label: "1" },
  { v: 3, label: "3" },
  { v: 8, label: "8" },
  { v: 16, label: "16" },
  { v: 32, label: "32" },
  { v: 128, label: "128" },
  { v: 500, label: "500" },
  { v: 1000, label: "1000" },
];

export function ModelSearchPage({ onOpenDetails }: ModelSearchPageProps) {
  const {
    getFilteredModels,
    searchModels,
    isLoading,
    selectModel,
    filters,
    updateFilters,
  } = useModelStore();

  const models = getFilteredModels();

  // Local UI state.
  const [query, setQuery] = React.useState(filters.searchQuery ?? "");
  const [activeTab, setActiveTab] = React.useState<FiltersTab>("main");
  const [filtersOpen, setFiltersOpen] = React.useState(true);

  const [dennettSupport, setDennettSupport] = React.useState(false);
  const [weightMax, setWeightMax] = React.useState<number>(filters.weightRange?.[1] ?? 1000);
  const [selectedTasks, setSelectedTasks] = React.useState<string[]>(filters.selectedTasks ?? []);
  const [selectedLanguage, setSelectedLanguage] = React.useState<string | null>(null);
  const [selectedLicense, setSelectedLicense] = React.useState<string | null>(null);

  // Pagination (requested in the plan).
  const pageSize = 12;
  const [page, setPage] = React.useState(1);
  const totalPages = Math.max(1, Math.ceil(models.length / pageSize));
  const pagedModels = React.useMemo(() => {
    const start = (page - 1) * pageSize;
    return models.slice(start, start + pageSize);
  }, [models, page]);

  React.useEffect(() => {
    // Load popular models by default.
    searchModels("").catch(() => void 0);
  }, [searchModels]);

  // Reset paging when filters/search changes.
  React.useEffect(() => {
    setPage(1);
  }, [filters.searchQuery, filters.selectedTasks, filters.weightRange, filters.sortBy]);

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    updateFilters({ searchQuery: query });
    searchModels(query).catch(() => void 0);
  };

  const handleOpenDetails = (model: Model) => {
    selectModel(model);
    onOpenDetails();
  };

  const toggleTask = (taskId: string) => {
    setSelectedTasks((prev) => {
      const next = prev.includes(taskId) ? prev.filter((t) => t !== taskId) : [...prev, taskId];
      updateFilters({ selectedTasks: next });
      return next;
    });
  };

  const applyWeight = (nextMax: number) => {
    setWeightMax(nextMax);
    updateFilters({ weightRange: [filters.weightRange?.[0] ?? 0.1, nextMax] });
  };

  const cycleSort = () => {
    const order: FilterState["sortBy"][] = ["popular", "downloads", "recent"];
    const idx = order.indexOf(filters.sortBy);
    const next = order[(idx + 1) % order.length];
    updateFilters({ sortBy: next });
  };

  return (
    <div className="relative h-full text-white">
      {/* Background like in the reference */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute inset-0 bg-[radial-gradient(1100px_circle_at_62%_18%,rgba(40,96,255,0.55),transparent_62%)]" />
        <div className="absolute inset-0 bg-[radial-gradient(1000px_circle_at_80%_92%,rgba(64,84,180,0.35),transparent_60%)]" />
      </div>

      <div className="flex h-full flex-col gap-5">
        <SearchHeader
          query={query}
          setQuery={setQuery}
          onSubmit={onSubmit}
          isLoading={isLoading}
          modelsCount={models.length}
          sortBy={filters.sortBy}
          onSortClick={cycleSort}
          filtersOpen={filtersOpen}
          onToggleFilters={() => setFiltersOpen((v) => !v)}
        />

        <div
          className={cn(
            "grid flex-1 gap-6 overflow-hidden",
            filtersOpen ? "lg:grid-cols-[380px_1fr]" : "lg:grid-cols-1",
          )}
        >
          {filtersOpen ? (
            <FiltersPanel
              activeTab={activeTab}
              setActiveTab={setActiveTab}
              weightMax={weightMax}
              onChangeWeight={applyWeight}
              selectedTasks={selectedTasks}
              onToggleTask={toggleTask}
              dennettSupport={dennettSupport}
              setDennettSupport={setDennettSupport}
              selectedLanguage={selectedLanguage}
              setSelectedLanguage={setSelectedLanguage}
              selectedLicense={selectedLicense}
              setSelectedLicense={setSelectedLicense}
            />
          ) : null}

          <ResultsPanel
            isLoading={isLoading}
            total={models.length}
            page={page}
            totalPages={totalPages}
            onPageChange={setPage}
            models={pagedModels}
            onOpenDetails={handleOpenDetails}
          />
        </div>
      </div>
    </div>
  );
}

function SearchHeader({
  query,
  setQuery,
  onSubmit,
  isLoading,
  modelsCount,
  sortBy,
  onSortClick,
  filtersOpen,
  onToggleFilters,
}: {
  query: string;
  setQuery: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
  isLoading: boolean;
  modelsCount: number;
  sortBy: FilterState["sortBy"];
  onSortClick: () => void;
  filtersOpen: boolean;
  onToggleFilters: () => void;
}) {
  const sortLabel = sortBy === "popular" ? "Popular" : sortBy === "downloads" ? "Downloads" : "Recent";

  return (
    <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
      <form onSubmit={onSubmit} className="w-full lg:flex-1">
        <div
          className={cn(
            "relative rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10",
            "shadow-[0_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl",
          )}
        >
          <Search className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-white/60" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for models..."
            className="h-12 rounded-2xl border-transparent bg-transparent pl-11 pr-3 text-[12px] focus-visible:ring-0 focus-visible:ring-offset-0"
          />

          {/* UX: show tiny spinner in the field while loading */}
          {isLoading ? (
            <Loader2 className="absolute right-4 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-white/50" />
          ) : null}
        </div>
      </form>

      <div className="flex flex-wrap items-center gap-3">
        <Button
          type="button"
          variant="outline"
          size="icon"
          className={cn(
            "h-12 w-12 rounded-2xl bg-black/10",
            filtersOpen ? "border-[hsl(var(--tp-border))]" : "border-[hsl(var(--tp-blue))]",
          )}
          title={filtersOpen ? "Hide filters" : "Show filters"}
          onClick={onToggleFilters}
        >
          <Filter className="h-4 w-4" />
        </Button>

        <Button
          type="button"
          variant="outline"
          className="h-12 rounded-2xl bg-black/10 px-4"
          title="Sort"
          onClick={onSortClick}
        >
          {sortLabel}
          <ChevronDown className="ml-2 h-4 w-4" />
        </Button>

        <div className="hidden items-center gap-2 text-[12px] text-[hsl(var(--tp-muted))] md:flex">
          <span className="font-semibold text-white/80">Models:</span>
          <span>{modelsCount}</span>
        </div>

        <Button
          type="button"
          variant="ghost"
          className="h-12 rounded-2xl px-4 text-[12px] text-white/70 hover:text-white"
          title="(Placeholder) Import local model"
        >
          <Upload className="mr-2 h-4 w-4" />
          Import model from disk
        </Button>
      </div>
    </div>
  );
}

function FiltersPanel({
  activeTab,
  setActiveTab,
  weightMax,
  onChangeWeight,
  selectedTasks,
  onToggleTask,
  dennettSupport,
  setDennettSupport,
  selectedLanguage,
  setSelectedLanguage,
  selectedLicense,
  setSelectedLicense,
}: {
  activeTab: FiltersTab;
  setActiveTab: (t: FiltersTab) => void;
  weightMax: number;
  onChangeWeight: (v: number) => void;
  selectedTasks: string[];
  onToggleTask: (taskId: string) => void;
  dennettSupport: boolean;
  setDennettSupport: (v: boolean) => void;
  selectedLanguage: string | null;
  setSelectedLanguage: (v: string | null) => void;
  selectedLicense: string | null;
  setSelectedLicense: (v: string | null) => void;
}) {
  return (
    <Card className="h-full overflow-hidden bg-black/10 p-0">
      <ScrollArea className="h-full">
        <div className="p-4">
          <FilterTabs value={activeTab} onChange={setActiveTab} />

          <div className="mt-4 space-y-6">
            {activeTab === "main" ? (
              <>
                <WeightSection value={weightMax} onChange={onChangeWeight} />
                <TasksSection selected={selectedTasks} onToggle={onToggleTask} />

                <div className="flex items-center justify-between rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 p-3">
                  <div className="text-[12px] text-white/90">Поддержка Dennett</div>
                  <Switch checked={dennettSupport} onCheckedChange={setDennettSupport} />
                </div>
              </>
            ) : null}

            {activeTab === "tasks" ? (
              <TasksSection selected={selectedTasks} onToggle={onToggleTask} dense />
            ) : null}

            {activeTab === "languages" ? (
              <PillGrid
                title="Languages"
                options={LANGUAGES}
                value={selectedLanguage}
                onChange={setSelectedLanguage}
              />
            ) : null}

            {activeTab === "license" ? (
              <PillGrid
                title="License"
                options={LICENSES}
                value={selectedLicense}
                onChange={setSelectedLicense}
              />
            ) : null}
          </div>
        </div>
      </ScrollArea>
    </Card>
  );
}

function ResultsPanel({
  isLoading,
  total,
  page,
  totalPages,
  onPageChange,
  models,
  onOpenDetails,
}: {
  isLoading: boolean;
  total: number;
  page: number;
  totalPages: number;
  onPageChange: (p: number) => void;
  models: Model[];
  onOpenDetails: (m: Model) => void;
}) {
  return (
    <div className="h-full overflow-hidden">
      <ScrollArea className="h-full">
        <div className="pb-10 pr-2">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="text-[11px] text-[hsl(var(--tp-muted))]">
              {isLoading
                ? "Searching models on Hugging Face…"
                : total
                  ? `${total} models found`
                  : "No models — try another query"}
            </div>

            <PaginationBar page={page} totalPages={totalPages} onChange={onPageChange} />
          </div>

          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {isLoading && total === 0
              ? Array.from({ length: 12 }).map((_, idx) => <ModelTileSkeleton key={idx} />)
              : models.map((m) => <ModelTile key={m.id} model={m} onClick={() => onOpenDetails(m)} />)}
          </div>
        </div>
      </ScrollArea>
    </div>
  );
}

function PaginationBar({
  page,
  totalPages,
  onChange,
}: {
  page: number;
  totalPages: number;
  onChange: (p: number) => void;
}) {
  // Keep it simple (Ozon-like, but compact): Prev 1 2 3 Next
  const numbers = React.useMemo(() => {
    const out: number[] = [];
    const start = Math.max(1, page - 2);
    const end = Math.min(totalPages, page + 2);
    for (let i = start; i <= end; i++) out.push(i);
    return out;
  }, [page, totalPages]);

  return (
    <div className="flex items-center gap-2">
      <Button
        type="button"
        variant="outline"
        className="h-8 rounded-xl bg-black/10 px-3 text-[11px]"
        onClick={() => onChange(Math.max(1, page - 1))}
        disabled={page <= 1}
      >
        Prev
      </Button>

      <div className="flex items-center gap-1">
        {numbers.map((n) => (
          <button
            key={n}
            type="button"
            onClick={() => onChange(n)}
            className={cn(
              "h-8 min-w-8 rounded-xl px-3 text-[11px] font-semibold transition-colors",
              n === page
                ? "bg-[hsl(var(--card))] text-white border border-[hsl(var(--tp-border))]"
                : "bg-black/10 text-white/70 hover:text-white hover:bg-white/10 border border-[hsl(var(--tp-border))]",
            )}
          >
            {n}
          </button>
        ))}
      </div>

      <Button
        type="button"
        variant="outline"
        className="h-8 rounded-xl bg-black/10 px-3 text-[11px]"
        onClick={() => onChange(Math.min(totalPages, page + 1))}
        disabled={page >= totalPages}
      >
        Next
      </Button>
    </div>
  );
}

function FilterTabs({
  value,
  onChange,
}: {
  value: FiltersTab;
  onChange: (tab: FiltersTab) => void;
}) {
  const tabs: Array<{ id: FiltersTab; label: string }> = [
    { id: "main", label: "Main" },
    { id: "tasks", label: "Tasks" },
    { id: "languages", label: "Languages" },
    { id: "license", label: "Lisence" },
  ];

  return (
    <div className="rounded-xl border border-[hsl(var(--tp-border))] bg-black/10 p-1">
      <div className="grid grid-cols-4 gap-1">
        {tabs.map((t) => {
          const active = value === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onChange(t.id)}
              className={cn(
                "h-8 rounded-lg text-[11px] font-semibold transition-colors",
                active
                  ? "bg-[hsl(var(--card))] text-white"
                  : "text-[hsl(var(--tp-muted))] hover:bg-white/5 hover:text-white",
              )}
            >
              {t.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function SectionTitle({ title }: { title: string }) {
  return <div className="text-[12px] font-semibold text-white/90">{title}</div>;
}

function WeightSection({ value, onChange }: { value: number; onChange: (v: number) => void }) {
  const minLabel = formatWeight(0.1);
  const maxLabel = formatWeight(value);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <SectionTitle title="Weight" />
        <div className="text-[12px] text-[hsl(var(--tp-muted))]">
          {minLabel} | {maxLabel}
        </div>
      </div>

      <div className="space-y-2">
        <input
          type="range"
          min={0.1}
          max={1000}
          step={0.1}
          value={value}
          onChange={(e) => onChange(Number(e.target.value))}
          className="w-full accent-[hsl(var(--tp-blue))]"
          aria-label="Weight"
        />

        <div className="flex justify-between gap-1 text-[10px] text-[hsl(var(--tp-muted))]">
          {WEIGHT_TICKS.map((t) => (
            <div key={t.label} className="w-full text-center">
              {t.label}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function TasksSection({
  selected,
  onToggle,
  dense,
}: {
  selected: string[];
  onToggle: (taskId: string) => void;
  dense?: boolean;
}) {
  return (
    <div className="space-y-3">
      <SectionTitle title="Tasks" />

      <div className={cn("grid gap-2", dense ? "grid-cols-1" : "grid-cols-2")}> 
        {TASKS.map((t) => {
          const active = selected.includes(t.id);
          const Icon = t.icon;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => onToggle(t.id)}
              className={cn(
                "flex items-center justify-between gap-2 rounded-xl border px-3 py-2 text-left transition-colors",
                active
                  ? "border-[hsl(var(--tp-blue))] bg-white/10 text-white"
                  : "border-[hsl(var(--tp-border))] bg-black/10 text-white/80 hover:bg-white/5",
              )}
            >
              <span className="flex min-w-0 items-center gap-2">
                <span
                  className={cn(
                    "flex h-7 w-7 items-center justify-center rounded-lg border",
                    active
                      ? "border-[hsl(var(--tp-blue))] bg-black/20"
                      : "border-[hsl(var(--tp-border))] bg-black/20",
                  )}
                >
                  <Icon className="h-4 w-4" />
                </span>
                <span className="truncate text-[11px]">{t.label}</span>
              </span>

              {t.extra ? (
                <span className="text-[10px] text-white/50">{t.extra}</span>
              ) : null}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function PillGrid({
  title,
  options,
  value,
  onChange,
}: {
  title: string;
  options: string[];
  value: string | null;
  onChange: (v: string | null) => void;
}) {
  return (
    <div className="space-y-3">
      <SectionTitle title={title} />
      <div className="grid grid-cols-2 gap-2">
        {options.map((opt) => {
          const active = value === opt;
          return (
            <button
              key={opt}
              type="button"
              onClick={() => onChange(active ? null : opt)}
              className={cn(
                "rounded-xl border px-3 py-2 text-left text-[11px] transition-colors",
                active
                  ? "border-[hsl(var(--tp-blue))] bg-white/10 text-white"
                  : "border-[hsl(var(--tp-border))] bg-black/10 text-white/80 hover:bg-white/5",
              )}
            >
              {opt}
            </button>
          );
        })}
      </div>
    </div>
  );
}

function ModelTile({ model, onClick }: { model: Model; onClick: () => void }) {
  const taskLabel = model.description || model.type || "Text generation";
  const sizeLabel = model.size && model.size !== "Unknown" ? model.size : "XL 22B";

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group w-full rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 p-4 text-left",
        "shadow-[0px_18px_50px_rgba(0,0,0,0.55)] backdrop-blur-2xl",
        "hover:bg-white/5 transition-colors",
      )}
    >
      <div className="truncate text-[14px] font-semibold text-white/90">{model.name}</div>
      <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-white/75">
        <span className="truncate">{taskLabel}</span>
        <Dot />
        <span className="truncate">{sizeLabel}</span>
        <Dot />
        <span className="truncate">↓ {model.downloads || "—"}</span>
      </div>
      <div className="mt-2 text-[11px] text-[hsl(var(--tp-muted))]">Updated: {model.updated || "—"}</div>
    </button>
  );
}

function ModelTileSkeleton() {
  return (
    <div className="w-full rounded-2xl border border-[hsl(var(--tp-border))] bg-black/10 p-4">
      <div className="space-y-2">
        <div className="h-4 w-40 animate-pulse rounded bg-white/10" />
        <div className="h-3 w-56 animate-pulse rounded bg-white/5" />
        <div className="h-3 w-32 animate-pulse rounded bg-white/5" />
      </div>
    </div>
  );
}

function Dot() {
  return <span className="h-1 w-1 rounded-full bg-[hsl(var(--tp-border))]" />;
}

function formatWeight(value: number) {
  if (value >= 1000) return "1000B";
  if (value >= 1) return `${value.toFixed(value < 10 ? 2 : value < 100 ? 1 : 0)}B`;
  return `${value.toFixed(1)}B`;
}
