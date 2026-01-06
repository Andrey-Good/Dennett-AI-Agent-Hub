import * as React from "react";
import { Filter, Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useModelStore } from "@/stores/modelStore";
import type { Model } from "@/types";

interface ModelSearchPageProps {
  onOpenDetails: () => void;
}

export function ModelSearchPage({ onOpenDetails }: ModelSearchPageProps) {
  const { getFilteredModels, searchModels, isLoading, selectModel } = useModelStore();
  const models = getFilteredModels();
  const [query, setQuery] = React.useState("");

  React.useEffect(() => {
    searchModels("").catch(() => void 0);
  }, [searchModels]);

  const onSubmit = (event: React.FormEvent) => {
    event.preventDefault();
    searchModels(query).catch(() => void 0);
  };

  const handleOpenDetails = (model: Model) => {
    selectModel(model);
    onOpenDetails();
  };

  return (
    <div className="h-full text-white">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="text-[11px] text-[hsl(var(--tp-muted))]">Inbox / Model Explorer</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-tight">Search models</h1>
          <p className="mt-1 text-[11px] text-[hsl(var(--tp-muted))]">
            Hugging Face registry + local models. Click a row to open the model card.
          </p>
        </div>

        <Button
          variant="outline"
          className="h-9 gap-2 rounded-xl bg-[hsl(var(--card))] px-3"
        >
          <Filter className="h-4 w-4" />
          Filters
        </Button>
      </div>

      {/* Search */}
      <form
        onSubmit={onSubmit}
        className="mt-6 flex items-center gap-3 rounded-[18px] border border-[hsl(var(--tp-border))] bg-[hsl(var(--card))] p-4 shadow-[0_18px_50px_rgba(0,0,0,0.55)]"
      >
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--tp-faint))]" />
          <Input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by model, task, author or tag…"
            className="h-9 rounded-xl bg-[hsl(var(--tp-sidebar))] pl-9"
          />
        </div>

        <Button type="submit" className="h-9 rounded-xl px-4">
          {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
          Search
        </Button>
      </form>

      {/* Results */}
      <div className="mt-6">
        <Card className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="text-[11px] text-[hsl(var(--tp-muted))]">
              {isLoading
                ? "Searching models on Hugging Face…"
                : models.length
                  ? `${models.length} models found`
                  : "No models — try another query"}
            </div>

            <div className="flex items-center gap-2 text-[11px] text-[hsl(var(--tp-muted))]">
              <span className="h-1.5 w-1.5 rounded-full bg-[#56a18a]" />
              Online
            </div>
          </div>

          <div className="mt-4 overflow-hidden rounded-2xl border border-[hsl(var(--tp-border))]">
            <div className="grid grid-cols-[1.6fr_0.6fr_0.6fr_0.6fr] bg-[hsl(var(--tp-sidebar))] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--tp-muted))]">
              <div>Model</div>
              <div>Task</div>
              <div>Downloads</div>
              <div>Updated</div>
            </div>

            <div className="divide-y divide-[hsl(var(--tp-border))]">
              {isLoading && models.length === 0
                ? Array.from({ length: 8 }).map((_, idx) => (
                    <RowSkeleton key={idx} />
                  ))
                : models.map((m) => (
                    <button
                      key={m.id}
                      type="button"
                      className={cn(
                        "grid w-full grid-cols-[1.6fr_0.6fr_0.6fr_0.6fr] items-center px-4 py-3 text-left transition-colors",
                        "hover:bg-[hsl(var(--secondary))]",
                      )}
                      onClick={() => handleOpenDetails(m)}
                    >
                      <div className="min-w-0">
                        <div className="truncate text-[12px] font-semibold text-white/90">{m.name}</div>
                        <div className="mt-0.5 truncate text-[11px] text-[hsl(var(--tp-muted))]">{m.id}</div>
                      </div>

                      <div className="text-[11px] text-[hsl(var(--tp-muted))]">{m.type}</div>
                      <div className="text-[11px] text-[hsl(var(--tp-muted))]">{m.downloads ?? "—"}</div>
                      <div className="text-[11px] text-[hsl(var(--tp-muted))]">{m.updated ?? "—"}</div>
                    </button>
                  ))}
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}

function RowSkeleton() {
  return (
    <div className="grid grid-cols-[1.6fr_0.6fr_0.6fr_0.6fr] items-center px-4 py-3">
      <div className="space-y-2">
        <div className="h-3 w-52 animate-pulse rounded bg-white/10" />
        <div className="h-3 w-36 animate-pulse rounded bg-white/5" />
      </div>
      <div className="h-3 w-20 animate-pulse rounded bg-white/5" />
      <div className="h-3 w-16 animate-pulse rounded bg-white/5" />
      <div className="h-3 w-20 animate-pulse rounded bg-white/5" />
    </div>
  );
}
