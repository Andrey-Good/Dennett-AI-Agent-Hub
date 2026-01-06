import * as React from "react";
import { Search } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { cn } from "@/lib/utils";

type HubCategory = {
  id: string;
  label: string;
};

type HubCard = {
  id: string;
  title: string;
  active: boolean;
  activation: string;
  lastRun: string;
  categoryId: string;
};

const CATEGORIES: HubCategory[] = [
  { id: "agent-architect", label: "Архитектор агентов" },
  { id: "calendar", label: "Создание записей в расписании" },
  { id: "brainstorm", label: "Мозговой штурмовик" },
  { id: "english", label: "Репетитор по английскому" },
  { id: "food", label: "Заказ ужина" },
  { id: "news", label: "Анализатор новостей" },
  { id: "work", label: "Быстрая сводка по работе" },
  { id: "calories", label: "Подсчёт калорий по фото" },
  { id: "chores", label: "Распределение обязанностей" },
  { id: "code", label: "Поиск кода по 1 строчке" },
  { id: "training", label: "Расписание тренировок" },
];

const CARDS: HubCard[] = Array.from({ length: 12 }).map((_, i) => {
  const categoryId = CATEGORIES[i % CATEGORIES.length].id;
  const active = i % 3 !== 1;
  return {
    id: `hub-${i}`,
    title: "Распределение задач по команде",
    active,
    activation: i % 2 === 0 ? "по триггеру" : "по времени",
    lastRun: "7 days ago",
    categoryId,
  };
});

export function HubPage({ onOpenAgent }: { onOpenAgent: (agentId: string) => void }) {
  const [activeCategory, setActiveCategory] = React.useState<string>(CATEGORIES[0]?.id ?? "");
  const [query, setQuery] = React.useState("");

  const filtered = React.useMemo(() => {
    return CARDS.filter((c) => {
      const matchCategory = !activeCategory || c.categoryId === activeCategory;
      const q = query.trim().toLowerCase();
      const matchQuery = !q || c.title.toLowerCase().includes(q);
      return matchCategory && matchQuery;
    });
  }, [activeCategory, query]);

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <ScrollArea className="w-full">
          <div className="flex w-max items-center gap-2 pr-6">
            {CATEGORIES.map((c) => {
              const isActive = c.id === activeCategory;
              return (
                <Button
                  key={c.id}
                  type="button"
                  size="sm"
                  variant={isActive ? "secondary" : "outline"}
                  onClick={() => setActiveCategory(c.id)}
                  className={cn(
                    "h-8 rounded-full px-4 text-xs font-medium",
                    isActive
                      ? "border-transparent bg-muted/70 text-foreground"
                      : "border-border/75 bg-background/30 text-muted-foreground hover:bg-muted/30 hover:text-foreground"
                  )}
                >
                  {c.label}
                </Button>
              );
            })}
          </div>
        </ScrollArea>

        <div className="hidden w-[320px] shrink-0 sm:block">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for models..."
              className="pl-9"
            />
          </div>
        </div>
      </div>

      <div className="grid flex-1 grid-cols-1 gap-3 overflow-hidden md:grid-cols-2 xl:grid-cols-3">
        <ScrollArea className="col-span-full h-full">
          <div className="grid grid-cols-1 gap-3 pb-6 md:grid-cols-2 xl:grid-cols-3">
            {filtered.map((c) => (
              <Card
                key={c.id}
                className="cursor-pointer transition-colors hover:bg-muted/15"
                onClick={() => onOpenAgent(c.categoryId)}
              >
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-semibold">{c.title}</CardTitle>
                </CardHeader>
                <CardContent className="space-y-3 text-xs text-muted-foreground">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "h-2 w-2 rounded-full",
                          c.active ? "bg-green-500" : "bg-red-500"
                        )}
                      />
                      <span>{c.active ? "Активен" : "Не активен"}</span>
                    </div>
                    <Badge variant="outline" className="bg-background/30">
                      {c.activation}
                    </Badge>
                  </div>

                  <div className="space-y-1">
                    <div>Активация: {c.activation}</div>
                    <div>Последний запуск: {c.lastRun}</div>
                  </div>

                  <div className="flex justify-end">
                    <Button size="sm" variant="secondary" className="rounded-lg">
                      Запустить
                    </Button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
