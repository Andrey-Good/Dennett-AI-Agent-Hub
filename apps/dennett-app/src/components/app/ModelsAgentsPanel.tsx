import * as React from "react";
import { Search } from "lucide-react";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { cn } from "@/lib/utils";
import { useModelStore } from "@/stores/modelStore";

type ModelsAgentsPanelProps = {
  className?: string;
};

const fallbackModels = [
  {
    id: "unsloth/DeepSeek-V3.1-Terminus-GGUF",
    name: "unsloth/DeepSeek-V3.1-Terminus-GGUF",
    task: "Text generation",
    params: "XL 22B",
    size: "3.9 ml.",
    updated: "7 days ago",
    latency: "15.2 ms",
  },
  {
    id: "mistral/Mixtral-8x7B-Instruct",
    name: "mistral/Mixtral-8x7B-Instruct",
    task: "Text generation",
    params: "8x7B",
    size: "4.1 ml.",
    updated: "12 days ago",
    latency: "19.0 ms",
  },
];

const fallbackAgents = [
  {
    id: "agent-1",
    name: "unsloth/DeepSeek-V3.1-Terminus-GGUF",
    task: "Agent",
    updated: "7 days ago",
    latency: "15.2 ms",
  },
  {
    id: "agent-2",
    name: "mistral/Mixtral-8x7B-Instruct",
    task: "Agent",
    updated: "2 days ago",
    latency: "21.1 ms",
  },
];

function SmallSearchInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
}) {
  return (
    <div className="relative">
      <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
      <Input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="h-10 rounded-xl bg-black/15 pl-9"
      />
    </div>
  );
}

function ItemCard({
  title,
  subtitle,
  meta,
  className,
}: {
  title: string;
  subtitle: string;
  meta: string;
  className?: string;
}) {
  return (
    <Card className={cn("rounded-2xl bg-black/15", className)}>
      <CardContent className="p-4">
        <div className="text-sm font-medium text-foreground/95 line-clamp-2">
          {title}
        </div>
        <div className="mt-2 text-[11px] text-muted-foreground">{subtitle}</div>
        <div className="mt-1 text-[11px] text-muted-foreground">{meta}</div>
      </CardContent>
    </Card>
  );
}

export function ModelsAgentsPanel({ className }: ModelsAgentsPanelProps) {
  const { models, searchModels } = useModelStore();
  const [modelQuery, setModelQuery] = React.useState("");
  const [agentQuery, setAgentQuery] = React.useState("");

  React.useEffect(() => {
    // try to warm up the list (if backend is up). If not, UI still shows fallback.
    void searchModels("");
  }, [searchModels]);

  const normalizedModels = (models?.length ? models : fallbackModels).map((m: any) => ({
    id: m.id ?? m.model_id ?? m.name,
    name: m.name ?? m.model_name ?? m.id,
    task: m.task ?? "Text generation",
    params: m.params ?? "XL 22B",
    size: m.size ?? "3.9 ml.",
    updated: m.updated ?? "7 days ago",
    latency: m.latency ?? "15.2 ms",
  }));

  const filteredModels = normalizedModels.filter((m) =>
    m.name.toLowerCase().includes(modelQuery.trim().toLowerCase())
  );
  const filteredAgents = fallbackAgents.filter((a) =>
    a.name.toLowerCase().includes(agentQuery.trim().toLowerCase())
  );

  return (
    <div className={cn("h-full w-[340px] shrink-0 p-4", className)}>
      <Card className="h-full rounded-[22px] bg-black/10">
        <CardHeader className="space-y-3 pb-3">
          <CardTitle className="text-sm font-semibold text-foreground/90">Models</CardTitle>
          <SmallSearchInput
            value={modelQuery}
            onChange={(v) => {
              setModelQuery(v);
              // optional: trigger server search when user types
              if (v.trim().length >= 2 || v.trim().length === 0) void searchModels(v);
            }}
            placeholder="Search for models..."
          />
        </CardHeader>

        <CardContent className="px-4 pb-4">
          <ScrollArea className="h-[380px] pr-3">
            <div className="space-y-3">
              {filteredModels.map((m) => (
                <ItemCard
                  key={m.id}
                  title={m.name}
                  subtitle={`${m.task}  ○  ${m.params}  ○  ${m.size}`}
                  meta={`Updated: ${m.updated}  ○  ${m.latency}`}
                />
              ))}
            </div>
          </ScrollArea>

          <Separator className="my-4" />

          <div className="space-y-3">
            <div className="text-sm font-semibold text-foreground/90">Agents</div>
            <SmallSearchInput
              value={agentQuery}
              onChange={setAgentQuery}
              placeholder="Search for agents..."
            />
            <ScrollArea className="h-[220px] pr-3">
              <div className="space-y-3">
                {filteredAgents.map((a) => (
                  <ItemCard
                    key={a.id}
                    title={a.name}
                    subtitle={`${a.task}`}
                    meta={`Updated: ${a.updated}  ○  ${a.latency}`}
                  />
                ))}
              </div>
            </ScrollArea>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
