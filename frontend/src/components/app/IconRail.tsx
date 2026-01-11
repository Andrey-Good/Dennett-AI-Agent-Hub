import * as React from "react";
import {
  Languages,
  LayoutGrid,
  MessageSquare,
  Mic,
  Search,
  SlidersHorizontal,
  Users,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type AppView = "hub" | "chat" | "models" | "settings";

type IconRailProps = {
  activeView: AppView;
  onNavigate: (view: AppView) => void;
};

export function IconRail({ activeView, onNavigate }: IconRailProps) {
  const items: Array<{ key: AppView; icon: React.ElementType; label: string }> = [
    { key: "hub", icon: LayoutGrid, label: "Hub" },
    { key: "chat", icon: MessageSquare, label: "Chat" },
    { key: "models", icon: Search, label: "Models" },
    { key: "settings", icon: SlidersHorizontal, label: "Settings" },
  ];

  return (
    <div
      className={cn(
        "w-[68px] shrink-0 border-r border-border/75 bg-black/35 backdrop-blur-md",
        "flex flex-col items-center justify-between py-4"
      )}
    >
      <div className="flex flex-col items-center gap-3">
        <div className="mb-1 flex h-11 w-11 items-center justify-center rounded-2xl bg-black/45 border border-border/75">
          <Mic className="h-5 w-5 text-foreground/90" />
        </div>

        <div className="flex flex-col items-center gap-2">
          {items.map((it) => {
            const Icon = it.icon;
            const active = activeView === it.key;
            return (
              <Button
                key={it.key}
                variant="ghost"
                size="icon"
                onClick={() => onNavigate(it.key)}
                className={cn(
                  "h-11 w-11 rounded-2xl",
                  active
                    ? "bg-white/10 border border-border/70"
                    : "text-muted-foreground hover:text-foreground hover:bg-white/10"
                )}
                aria-label={it.label}
              >
                <Icon className="h-5 w-5" />
              </Button>
            );
          })}

          {/* extra decorative icons (as in the mock) */}
          <div className="mt-2 flex flex-col items-center gap-2 opacity-70">
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-2xl text-muted-foreground hover:text-foreground"
              aria-label="Users"
            >
              <Users className="h-5 w-5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-10 w-10 rounded-2xl text-muted-foreground hover:text-foreground"
              aria-label="Language"
            >
              <Languages className="h-5 w-5" />
            </Button>
          </div>
        </div>
      </div>

      <div className="flex flex-col items-center gap-2">
        <div className="h-10 w-10 rounded-2xl border border-border/75 bg-black/25" />
      </div>
    </div>
  );
}
