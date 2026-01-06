import * as React from "react";

import { WindowChrome } from "@/components/app/WindowChrome";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { AppSidebar, type AppRoute } from "@/layout/AppSidebar";
import { ChatWithModelPage } from "@/views/ChatWithModelPage";
import { DashboardPage } from "@/views/DashboardPage";
import { ModelDetailsPanel } from "@/views/ModelDetailsPanel";
import { ModelHubPage } from "@/views/ModelHubPage";
import { ModelSearchPage } from "@/views/ModelSearchPage";
import { WorkflowBuilderPage } from "@/views/WorkflowBuilderPage";

/**
 * Root UI: Taskplus-inspired (palette, typography and shadows).
 */
export default function App() {
  const [activeRoute, setActiveRoute] = React.useState<AppRoute>("dashboard");
  const [detailsOpen, setDetailsOpen] = React.useState(false);

  return (
    /* Outer background (visible only in rounded corners / transparent window) */
    <div className="h-screen w-screen bg-[#50504f]">
      <div className="tp-window flex">
        <WindowChrome />

        <AppSidebar active={activeRoute} onChange={setActiveRoute} />

        <main className="relative flex flex-1 flex-col bg-[hsl(var(--background))]">
          <div className="h-full overflow-y-auto px-7 pb-6 pt-12">
            {activeRoute === "dashboard" && <DashboardPage />}
            {activeRoute === "modelHub" && <ModelHubPage onOpenDetails={() => setDetailsOpen(true)} />}
            {activeRoute === "modelSearch" && (
              <ModelSearchPage onOpenDetails={() => setDetailsOpen(true)} />
            )}
            {activeRoute === "workflow" && <WorkflowBuilderPage />}
            {activeRoute === "chat" && <ChatWithModelPage />}
            {activeRoute === "settings" && <SettingsPlaceholder />}
          </div>
        </main>

        <ModelDetailsPanel open={detailsOpen} onClose={() => setDetailsOpen(false)} />
      </div>
    </div>
  );
}

function SettingsPlaceholder() {
  return (
    <div className="flex h-full items-center justify-center">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle className="text-base text-white">Settings</CardTitle>
        </CardHeader>
        <CardContent className="text-[12px] leading-relaxed text-[hsl(var(--tp-muted))]">
          Экран настроек можно расширить позже. Сейчас здесь оставлен экран-заглушка,
          оформленный в стиле Taskplus.
        </CardContent>
      </Card>
    </div>
  );
}
