import * as React from "react";
import {
  Bell,
  Box,
  CalendarDays,
  Folder,
  HelpCircle,
  Inbox,
  LayoutDashboard,
  Plus,
  Search,
  Settings,
  Sparkles,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export type AppRoute =
  | "dashboard"
  | "modelHub"
  | "modelSearch"
  | "workflow"
  | "chat"
  | "settings";

interface AppSidebarProps {
  active: AppRoute;
  onChange: (route: AppRoute) => void;
}

type Item = {
  id: string;
  label: string;
  icon: React.ComponentType<React.SVGProps<SVGSVGElement>>;
  route?: AppRoute;
};

const topItems: Item[] = [
  { id: "search", label: "Search", icon: Search, route: "modelSearch" },
  { id: "ai", label: "Dennett AI", icon: Sparkles, route: "chat" },
  { id: "templates", label: "Templates", icon: Folder, route: "workflow" },
  { id: "notifications", label: "Notification", icon: Bell },
];

const mainItems: Item[] = [
  { id: "dashboard", label: "Dashboard", icon: LayoutDashboard, route: "dashboard" },
  { id: "inbox", label: "Inbox", icon: Inbox, route: "chat" },
  { id: "project", label: "Project", icon: Folder, route: "modelHub" },
  { id: "calendar", label: "Calendar", icon: CalendarDays, route: "workflow" },
  { id: "help", label: "Help & Center", icon: HelpCircle },
  { id: "settings", label: "Settings", icon: Settings, route: "settings" },
];

export function AppSidebar({ active, onChange }: AppSidebarProps) {
  return (
    <aside className="tp-sidebar flex h-full flex-col px-4 pb-5 pt-4">
      {/* Brand */}
      <div className="mb-5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Plus className="h-4 w-4 text-white" />
          <span className="text-[14px] font-semibold text-white">Dennett</span>
        </div>

        <button
          type="button"
          className="flex h-7 w-7 items-center justify-center rounded-full bg-[hsl(var(--card))] text-[10px] font-semibold text-white/90 shadow-[inset_0_1px_0_rgba(255,255,255,0.08)]"
          aria-label="Profile"
        >
          AC
        </button>
      </div>

      <nav className="space-y-1">
        {topItems.map((item) => (
          <SidebarItem
            key={item.id}
            item={item}
            active={item.route ? active === item.route : false}
            onClick={() => item.route && onChange(item.route)}
          />
        ))}
      </nav>

      <div className="my-4 tp-separator" />

      <nav className="space-y-1">
        {mainItems.map((item) => (
          <SidebarItem
            key={item.id}
            item={item}
            active={item.route ? active === item.route : false}
            onClick={() => item.route && onChange(item.route)}
          />
        ))}
      </nav>

      <div className="mt-auto">
        <UpgradeCard />
      </div>
    </aside>
  );
}

function SidebarItem({
  item,
  active,
  onClick,
}: {
  item: Item;
  active?: boolean;
  onClick?: () => void;
}) {
  const Icon = item.icon;
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex w-full items-center gap-3 rounded-xl px-3 py-2 text-[12px] font-medium transition-colors",
        active
          ? "border border-[hsl(var(--tp-border))] bg-[hsl(var(--card))] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]"
          : "text-[hsl(var(--tp-muted))] hover:bg-[hsl(var(--card))] hover:text-white",
      )}
    >
      <Icon
        className={cn(
          "h-4 w-4",
          active ? "text-white" : "text-[hsl(var(--tp-muted))] group-hover:text-white",
        )}
      />
      <span className="truncate">{item.label}</span>
    </button>
  );
}

function UpgradeCard() {
  return (
    <div className="relative mt-6 overflow-hidden rounded-[20px] border border-[hsl(var(--tp-border))] bg-[linear-gradient(180deg,#202022_0%,#141416_100%)] p-4 shadow-[0_22px_70px_rgba(0,0,0,0.7)]">
      <button
        type="button"
        className="absolute right-3 top-3 text-[hsl(var(--tp-faint))] hover:text-white"
        aria-label="Close"
      >
        ×
      </button>

      <div className="mb-3 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-[hsl(var(--tp-sidebar))] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
          <Box className="h-5 w-5 text-white/90" />
        </div>
        <div className="space-y-0.5">
          <div className="text-[14px] font-semibold text-white">Upgrade to Pro!</div>
          <div className="text-[11px] leading-snug text-[hsl(var(--tp-muted))]">
            Unlock Premium Features and<br />Manage Unlimited projects
          </div>
        </div>
      </div>

      <Button
        variant="secondary"
        className="h-9 w-full rounded-xl bg-[hsl(var(--card))] text-[12px] font-semibold text-white hover:bg-[hsl(var(--secondary))]"
      >
        Upgrade Now
      </Button>
    </div>
  );
}
