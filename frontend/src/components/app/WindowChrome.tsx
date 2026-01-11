import type React from "react";
import { Minus, Square, X } from "lucide-react";
import { Button } from "@/components/ui/button";

/**
 * Custom titlebar for undecorated Tauri window (v2).
 * Styled to blend into the Taskplus-inspired UI.
 */
function isTauriRuntime() {
  return (
    typeof window !== "undefined" &&
    (("__TAURI_INTERNALS__" in window as any) || ("__TAURI__" in window as any))
  );
}

let cachedWindowPromise: Promise<any> | null = null;

async function getAppWindow() {
  if (!cachedWindowPromise) {
    cachedWindowPromise = import("@tauri-apps/api/window").then((mod: any) => mod.getCurrentWindow());
  }
  return cachedWindowPromise;
}

async function safeWindowCall<T>(fn: (w: any) => Promise<T>) {
  if (!isTauriRuntime()) return null as any;
  try {
    const w = await getAppWindow();
    return await fn(w);
  } catch (e) {
    console.error("[WindowChrome] window call failed:", e);
    return null as any;
  }
}

export function WindowChrome() {
  const handleDragMouseDown = async (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    await safeWindowCall((w) => w.startDragging());
  };

  return (
    <div className="absolute left-0 right-0 top-0 z-50 flex h-11 items-center px-4">
      {/* Drag region */}
      <div className="h-full flex-1" data-tauri-drag-region onMouseDown={handleDragMouseDown} />

      {/* Window controls */}
      <div className="flex items-center gap-1" data-tauri-drag-region="false">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          data-tauri-drag-region="false"
          className="h-8 w-8 rounded-lg text-[hsl(var(--tp-muted))] hover:bg-[hsl(var(--card))] hover:text-white"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={() => safeWindowCall((w) => w.minimize())}
          title="Свернуть"
        >
          <Minus className="h-4 w-4" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          data-tauri-drag-region="false"
          className="h-8 w-8 rounded-lg text-[hsl(var(--tp-muted))] hover:bg-[hsl(var(--card))] hover:text-white"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={async () => {
            const isMax = await safeWindowCall((w) => w.isMaximized());
            if (isMax) await safeWindowCall((w) => w.unmaximize());
            else await safeWindowCall((w) => w.maximize());
          }}
          title="Развернуть"
        >
          <Square className="h-3.5 w-3.5" />
        </Button>

        <Button
          type="button"
          variant="ghost"
          size="icon"
          data-tauri-drag-region="false"
          className="h-8 w-8 rounded-lg text-[hsl(var(--tp-muted))] hover:bg-red-500/25 hover:text-white"
          onMouseDown={(e) => e.stopPropagation()}
          onClick={() => safeWindowCall((w) => w.close())}
          title="Закрыть"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
