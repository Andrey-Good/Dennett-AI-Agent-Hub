import * as React from "react";
import { ArrowUp, Clock, MoreHorizontal, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { useModelStore } from "@/stores/modelStore";

type MessageRole = "assistant" | "user";

type Message = {
  id: string;
  role: MessageRole;
  text: string;
};

export function ChatWithModelPage() {
  const { localModels, selectedModel, selectModel, fetchLocalModels } = useModelStore();
  const [messages, setMessages] = React.useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      text: "Hi! I'm your Dennett sandbox. Pick a model on the right and start chatting.",
    },
  ]);
  const [prompt, setPrompt] = React.useState("");

  React.useEffect(() => {
    if (!localModels.length) {
      fetchLocalModels().catch(() => void 0);
    }
  }, [fetchLocalModels, localModels.length]);

  const onSend = () => {
    const trimmed = prompt.trim();
    if (!trimmed) return;

    const userMessage: Message = {
      id: String(Date.now()),
      role: "user",
      text: trimmed,
    };

    // Placeholder assistant reply.
    const echo: Message = {
      id: String(Date.now() + 1),
      role: "assistant",
      text: "Stub reply from the selected model. Wire this up to your backend inference endpoint.",
    };

    setMessages((m) => [...m, userMessage, echo]);
    setPrompt("");
  };

  const onKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSend();
    }
  };

  return (
    <div className="grid h-full grid-cols-[minmax(0,1.55fr)_minmax(0,280px)] gap-4 text-white">
      {/* Chat */}
      <Card className="flex h-full flex-col overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-[hsl(var(--tp-border))] px-4 py-3">
          <div>
            <div className="text-[12px] font-semibold">Chat</div>
            <div className="mt-0.5 text-[11px] text-[hsl(var(--tp-muted))]">
              Conversation sandbox for a single model.
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge className="border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] text-white/80">
              <Clock className="mr-1 h-3 w-3" />
              Temp: 0.7
            </Badge>

            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl">
              <RefreshCw className="h-4 w-4" />
            </Button>
            <Button variant="ghost" size="icon" className="h-9 w-9 rounded-xl">
              <MoreHorizontal className="h-4 w-4" />
            </Button>
          </div>
        </div>

        <div className="flex flex-1 flex-col">
          <ScrollArea className="flex-1">
            <div className="space-y-4 px-5 py-5">
              {messages.map((m) => (
                <div key={m.id} className={m.role === "user" ? "flex justify-end" : "flex justify-start"}>
                  <div
                    className={
                      m.role === "user"
                        ? "max-w-[72%] rounded-2xl border border-[#33407a] bg-[#283454] px-4 py-2 text-[12px] text-white shadow-[0_18px_50px_rgba(0,0,0,0.55)]"
                        : "max-w-[72%] rounded-2xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--card))] px-4 py-2 text-[12px] text-white/90 shadow-[0_18px_50px_rgba(0,0,0,0.55)]"
                    }
                  >
                    {m.text}
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="border-t border-[hsl(var(--tp-border))] p-4">
            <div className="flex items-center gap-2 rounded-[18px] border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] px-3 py-2">
              <Input
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                onKeyDown={onKeyDown}
                placeholder={
                  selectedModel
                    ? `Ask something to ${selectedModel.name}…`
                    : "Select a model on the right to start chatting…"
                }
                className="h-9 border-none bg-transparent px-0"
              />
              <Button
                size="icon"
                className="h-9 w-9 rounded-2xl"
                onClick={onSend}
                disabled={!prompt.trim()}
              >
                <ArrowUp className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Model selector */}
      <Card className="flex h-full flex-col overflow-hidden">
        <div className="border-b border-[hsl(var(--tp-border))] px-4 py-3">
          <div className="text-[12px] font-semibold">Model selector</div>
          <div className="mt-0.5 text-[11px] text-[hsl(var(--tp-muted))]">
            Choose a local model to bind this chat to.
          </div>
        </div>

        <div className="flex flex-1 flex-col gap-3 p-4 text-[11px]">
          <div className="space-y-2">
            <label className="text-[11px] font-semibold text-white/80">Active model</label>

            <select
              value={selectedModel?.id ?? ""}
              onChange={(e) => {
                const id = e.target.value;
                const next = localModels.find((m: any) => m.id === id);
                if (next) selectModel(next as any);
              }}
              className="h-9 w-full rounded-xl border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] px-3 text-[11px] text-white/90 outline-none focus:ring-2 focus:ring-[hsl(var(--tp-blue))]"
            >
              <option value="">— Select model —</option>
              {localModels.map((m: any) => (
                <option key={m.id ?? m.name} value={m.id}>
                  {m.name ?? m.id}
                </option>
              ))}
            </select>
          </div>

          <div className="mt-2 rounded-[18px] border border-[hsl(var(--tp-border))] bg-[hsl(var(--tp-sidebar))] p-4">
            <div className="text-[12px] font-semibold text-white/90">Session hints</div>
            <ul className="mt-2 space-y-1 text-[11px] text-[hsl(var(--tp-muted))]">
              <li>• Use this space for quick checks and prompts.</li>
              <li>• For complex workflows, build an agent in Workflow.</li>
              <li>• Local-first — no cloud logging by default.</li>
            </ul>
          </div>

          <div className="mt-auto space-y-2 pt-2">
            <div className="flex items-center justify-between text-[11px] text-[hsl(var(--tp-muted))]">
              <span>Tokens used</span>
              <span>—</span>
            </div>
            <div className="flex items-center justify-between text-[11px] text-[hsl(var(--tp-muted))]">
              <span>Streaming</span>
              <span className="flex items-center gap-1 text-white/80">
                <span className="h-1.5 w-1.5 rounded-full bg-[#56a18a]" />
                Enabled
              </span>
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
}
