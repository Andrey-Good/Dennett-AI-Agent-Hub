import * as React from "react";
import { ArrowUp, Clock, MoreHorizontal, Plus, RotateCcw, Share2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";

type Message = {
  id: string;
  role: "assistant" | "user";
  text: string;
};

const DEFAULT_MESSAGES: Message[] = [
  {
    id: "m1",
    role: "assistant",
    text: "Hi, how can I help you today?\n\nNorth Star: Active Paying Subscribers (APS).\nPrimary drivers:\n- Trial → Paid Conversion Rate (7/14/30-day)\n- 90-day Churn Rate\n- ARPPU (average revenue per paying user)\n\nGuardrails: app crash rate, latency p95, support ticket rate, refund rate.\nKPI tree: Traffic → Qualified Trials → Activation → Paywall → Billing success → Retention → Expansion (upsells).",
  },
  {
    id: "m2",
    role: "user",
    text: "Before we dive in, what should be our core KPIs",
  },
  {
    id: "m3",
    role: "assistant",
    text: "Minimal model (daily grain): users, events, subscriptions, payments, marketing_attribution.\nData quality:\n- Uniqueness: users.user_id unique; subscriptions unique on (user_id,start_dt)\n- Completeness: required fields non-null (e.g., plan_id, currency)\n- Consistency: single global timezone (UTC), then localize in BI\n- Reasonableness: conversion windows within 0–30 days; negative prices blocked.",
  },
  {
    id: "m4",
    role: "user",
    text: "What data model and quality checks do we need first?",
  },
];

const DEFAULT_HISTORY = [
  "Hi, how can I help you today?",
  "Product Ideas — Brainstorm with AI",
  "Financial Model — Unit Economics",
  "A/B Test — Plan & MDE",
  "SQL Helper — Data Questions",
  "Dashboard Review — Weekly Metrics",
  "Demand Forecast — Q4 Scenarios",
  "UX Copy — Paywall Variations",
];

export function ChatPage() {
  const [prompt, setPrompt] = React.useState("");
  const [messages, setMessages] = React.useState<Message[]>(DEFAULT_MESSAGES);

  const onSend = () => {
    const trimmed = prompt.trim();
    if (!trimmed) return;
    setMessages((m) => [...m, { id: String(Date.now()), role: "user", text: trimmed }]);
    setPrompt("");
  };

  return (
    <div className="grid h-full grid-cols-[1fr_280px] gap-4">
      <Card className="h-full overflow-hidden">
        <CardHeader className="flex flex-row items-center justify-between gap-3 border-b border-border/50 py-3">
          <CardTitle className="text-sm font-semibold text-muted-foreground">Chat</CardTitle>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" aria-label="Share">
              <Share2 className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="History">
              <Clock className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="Reset">
              <RotateCcw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="New">
              <Plus className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" aria-label="More">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </div>
        </CardHeader>

        <CardContent className="flex h-[calc(100%-64px)] flex-col p-0">
          <ScrollArea className="flex-1 px-6 py-5">
            <div className="space-y-4">
              {messages.map((m) => (
                <div
                  key={m.id}
                  className={
                    m.role === "user"
                      ? "flex justify-end"
                      : "flex justify-start"
                  }
                >
                  <div
                    className={
                      m.role === "user"
                        ? "max-w-[70%] rounded-2xl bg-muted/70 px-4 py-2 text-sm"
                        : "max-w-[78%] whitespace-pre-line text-sm text-muted-foreground"
                    }
                  >
                    {m.text}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="border-t border-border/50 p-4">
            <div className="flex items-center gap-2 rounded-xl border border-border/75 bg-background/40 px-3 py-2">
              <Input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="Start Chat with agent..."
                className="border-0 bg-transparent px-0 focus-visible:ring-0"
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    onSend();
                  }
                }}
              />
              <Button size="icon" variant="ghost" onClick={onSend} aria-label="Send">
                <ArrowUp className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card className="h-full overflow-hidden">
        <CardHeader className="border-b border-border/50 py-3">
          <CardTitle className="text-sm font-semibold">History</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <div className="p-4">
            <div className="relative">
              <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                ⌕
              </span>
              <Input
                placeholder="Search for words..."
                className="pl-9"
              />
            </div>
          </div>
          <ScrollArea className="h-[calc(100%-80px)] px-2 pb-4">
            <div className="space-y-1 px-2">
              {DEFAULT_HISTORY.map((item) => (
                <button
                  key={item}
                  className="w-full rounded-lg px-3 py-2 text-left text-sm text-muted-foreground transition-colors hover:bg-muted/30 hover:text-foreground"
                >
                  {item}
                </button>
              ))}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  );
}
