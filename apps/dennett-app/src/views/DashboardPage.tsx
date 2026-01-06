import * as React from "react";
import {
  ArrowUpRight,
  FileDown,
  Filter,
  Folder,
  Search,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";

type Stat = {
  label: string;
  value: string | number;
  delta: string;
};

const stats: Stat[] = [
  { label: "Total Projects", value: 15, delta: "+5 vs last month" },
  { label: "Total Task", value: 10, delta: "+2 vs last month" },
  { label: "In Reviews", value: 23, delta: "+12 vs last month" },
  { label: "Completed Tasks", value: 50, delta: "+15 vs last month" },
];

const todayTasks = [
  { title: "Prepare Q2 report", project: "Fintech Project", tag: "blue", due: "12 Mar 2024" },
  { title: "Finalize homepage design", project: "Brodo Redesign", tag: "purple", due: "12 Mar 2024" },
  { title: "Review onboarding checklist", project: "HR Setup", tag: "green", due: "12 Mar 2024" },
  { title: "Finalize homepage design", project: "Lucas Projects", tag: "yellow", due: "12 Mar 2024" },
  { title: "Finalize homepage design", project: "All in One Project", tag: "violet", due: "12 Mar 2024" },
];

const projects = [
  {
    name: "Fintech Project",
    status: "In Progress" as const,
    progress: 70,
    total: "14 / 20",
    due: "12 Mar 2024",
    owner: "Michael M",
  },
  {
    name: "Brodo Redesign",
    status: "Completed" as const,
    progress: 100,
    total: "25 / 25",
    due: "16 Mar 2024",
    owner: "Jhon Cena",
  },
  {
    name: "HR Setup",
    status: "On Hold" as const,
    progress: 70,
    total: "8 / 20",
    due: "18 May 2024",
    owner: "Dawne Jay",
  },
];

export function DashboardPage() {
  return (
    <div className="h-full text-white">
      {/* Header */}
      <div className="flex items-start justify-between gap-6">
        <div>
          <div className="text-[11px] text-[hsl(var(--tp-muted))]">Dashboard</div>
          <h1 className="mt-1 text-[22px] font-semibold tracking-tight">
            Welcome Back, John Connor! <span className="align-middle">👋</span>
          </h1>
          <p className="mt-1 text-[11px] text-[hsl(var(--tp-muted))]">
            4 Tasks Due Today, 2 Overdue Tasks, 8 Upcoming Deadlines (This Week)
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="hidden text-[11px] text-[hsl(var(--tp-muted))] md:block">
            Last Updated 12 May 2024
          </div>

          <div className="flex -space-x-2">
            <AvatarBubble label="A" />
            <AvatarBubble label="C" />
            <AvatarBubble label="J" />
          </div>

          <Button
            variant="outline"
            className="h-9 gap-2 rounded-xl bg-[hsl(var(--card))] px-3 text-[11px] font-semibold"
          >
            <FileDown className="h-4 w-4" />
            Export
          </Button>
        </div>
      </div>

      {/* Stat cards */}
      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <MetricCard key={s.label} {...s} />
        ))}
      </div>

      {/* Middle row */}
      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-[1fr_360px]">
        <Card className="p-4">
          <div className="flex items-center justify-between gap-4">
            <div className="text-[13px] font-semibold">Today's Tasks</div>

            <div className="flex items-center gap-2">
              <div className="relative">
                <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--tp-faint))]" />
                <Input
                  placeholder="Search here..."
                  className="h-9 w-[220px] rounded-xl bg-[hsl(var(--tp-sidebar))] pl-9"
                />
              </div>
              <Button
                variant="outline"
                className="h-9 w-10 rounded-xl bg-[hsl(var(--card))] p-0"
                title="Filter"
              >
                <Filter className="h-4 w-4" />
              </Button>
            </div>
          </div>

          <div className="mt-4 overflow-hidden rounded-2xl border border-[hsl(var(--tp-border))]">
            <div className="grid grid-cols-[1.4fr_1fr_0.7fr] gap-0 bg-[hsl(var(--tp-sidebar))] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--tp-muted))]">
              <div>Task Name</div>
              <div>Project</div>
              <div>Due</div>
            </div>

            <div className="divide-y divide-[hsl(var(--tp-border))]">
              {todayTasks.map((t, idx) => (
                <div
                  key={`${t.title}-${idx}`}
                  className="grid grid-cols-[1.4fr_1fr_0.7fr] items-center gap-0 px-4 py-3 text-[12px]"
                >
                  <div className="truncate text-white/90">{t.title}</div>
                  <div className="flex items-center gap-2 text-[11px] text-[hsl(var(--tp-muted))]">
                    <span className={cn("h-2 w-2 rounded-sm", tagColor(t.tag))} />
                    {t.project}
                  </div>
                  <div className="text-[11px] text-[hsl(var(--tp-muted))]">{t.due}</div>
                </div>
              ))}
            </div>
          </div>
        </Card>

        <Card className="p-4">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-[12px] font-semibold">Performance</div>
              <div className="mt-2 flex items-baseline gap-2">
                <div className="text-[28px] font-semibold tracking-tight">86%</div>
                <div className="text-[11px] text-[hsl(var(--tp-muted))]">+15% vs last Week</div>
              </div>
            </div>
          </div>

          <div className="mt-5 grid grid-cols-7 items-end gap-2">
            {[
              { day: "Mon", v: 82 },
              { day: "Tue", v: 51 },
              { day: "Wed", v: 86 },
              { day: "Thu", v: 45 },
              { day: "Fri", v: 82 },
              { day: "Sat", v: 64 },
              { day: "Sun", v: 70 },
            ].map((d) => (
              <div key={d.day} className="flex flex-col items-center gap-2">
                <div
                  className="w-7 rounded-xl bg-[hsl(var(--tp-sidebar))] shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]"
                  style={{ height: `${Math.max(18, d.v * 1.2)}px` }}
                />
                <div className="text-[9px] text-[hsl(var(--tp-muted))]">+{d.v}%</div>
              </div>
            ))}
          </div>

          <div className="mt-4 grid grid-cols-7 text-center text-[10px] text-[hsl(var(--tp-muted))]">
            {[
              "Mon",
              "Tue",
              "Wed",
              "Thu",
              "Fri",
              "Sat",
              "Sun",
            ].map((d) => (
              <div key={d}>{d}</div>
            ))}
          </div>
        </Card>
      </div>

      {/* List projects */}
      <Card className="mt-6 p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="text-[13px] font-semibold">List Projects</div>

          <div className="flex items-center gap-2">
            <div className="relative">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-[hsl(var(--tp-faint))]" />
              <Input
                placeholder="Search here..."
                className="h-9 w-[220px] rounded-xl bg-[hsl(var(--tp-sidebar))] pl-9"
              />
            </div>
            <Button
              variant="outline"
              className="h-9 w-10 rounded-xl bg-[hsl(var(--card))] p-0"
              title="Filter"
            >
              <Filter className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="mt-4 overflow-hidden rounded-2xl border border-[hsl(var(--tp-border))]">
          <div className="grid grid-cols-[1.2fr_0.8fr_1fr_0.7fr_0.8fr] gap-0 bg-[hsl(var(--tp-sidebar))] px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-[hsl(var(--tp-muted))]">
            <div>Project Name</div>
            <div>Status</div>
            <div>Progress</div>
            <div>Total Task</div>
            <div>Owner</div>
          </div>

          <div className="divide-y divide-[hsl(var(--tp-border))]">
            {projects.map((p) => (
              <div
                key={p.name}
                className="grid grid-cols-[1.2fr_0.8fr_1fr_0.7fr_0.8fr] items-center gap-0 px-4 py-3"
              >
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-sm bg-[hsl(var(--tp-blue))]" />
                  <span className="text-[12px] text-white/90">{p.name}</span>
                </div>

                <StatusPill status={p.status} />

                <div className="flex items-center gap-3">
                  <Progress value={p.progress} className="h-1.5" />
                  <div className="text-[11px] text-[hsl(var(--tp-muted))]">{p.progress}%</div>
                </div>

                <div className="text-[11px] text-[hsl(var(--tp-muted))]">{p.total}</div>

                <div className="flex items-center justify-end gap-2">
                  <div className="flex -space-x-2">
                    <AvatarBubble label={p.owner.split(" ")[0][0]} />
                    <AvatarBubble label={p.owner.split(" ")[1]?.[0] ?? "M"} />
                  </div>
                  <span className="hidden text-[11px] text-[hsl(var(--tp-muted))] xl:block">
                    {p.owner}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </Card>

      <div className="mt-6 flex items-center justify-end text-[11px] text-[hsl(var(--tp-muted))]">
        <button type="button" className="flex items-center gap-1 hover:text-white">
          View all
          <ArrowUpRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function MetricCard({ label, value, delta }: Stat) {
  return (
    <div className="rounded-[18px] border border-[hsl(var(--tp-border))] bg-[hsl(var(--card))] px-4 py-3 shadow-[0_18px_50px_rgba(0,0,0,0.55)]">
      <div className="flex items-start justify-between">
        <div>
          <div className="text-[11px] text-[hsl(var(--tp-muted))]">{label}</div>
          <div className="mt-1 text-[22px] font-semibold tracking-tight text-white">
            {value}
          </div>
          <div className="mt-1 text-[11px] text-[hsl(var(--tp-muted))]">{delta}</div>
        </div>

        <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] shadow-[inset_0_1px_0_rgba(255,255,255,0.06)]">
          <Folder className="h-5 w-5 text-white/30" />
        </div>
      </div>
    </div>
  );
}

function AvatarBubble({ label }: { label: string }) {
  return (
    <div className="flex h-7 w-7 items-center justify-center rounded-full border border-[hsl(var(--tp-border))] bg-[hsl(var(--card))] text-[10px] font-semibold text-white/90">
      {label}
    </div>
  );
}

type Status = "In Progress" | "Completed" | "On Hold";

function StatusPill({ status }: { status: Status }) {
  const classes =
    status === "In Progress"
      ? "bg-[hsl(var(--tp-blue-bg))] text-[#acb3c8]"
      : status === "Completed"
        ? "bg-[hsl(var(--tp-green-bg))] text-[#56a18a]"
        : "bg-[hsl(var(--tp-pill))] text-[hsl(var(--tp-muted))]";

  return (
    <div
      className={cn(
        "inline-flex w-fit items-center rounded-full px-3 py-1 text-[11px] font-medium",
        classes,
      )}
    >
      {status}
    </div>
  );
}

function tagColor(tag: string) {
  switch (tag) {
    case "blue":
      return "bg-[hsl(var(--tp-blue))]";
    case "purple":
      return "bg-[#704ccc]";
    case "green":
      return "bg-[#56a18a]";
    case "yellow":
      return "bg-[#b9a24a]";
    case "violet":
      return "bg-[#6d52c8]";
    default:
      return "bg-white/40";
  }
}
