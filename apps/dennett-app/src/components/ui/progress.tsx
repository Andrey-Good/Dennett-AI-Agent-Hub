import * as React from "react";
import { cn } from "@/lib/utils";

export interface ProgressProps extends React.HTMLAttributes<HTMLDivElement> {
  value?: number;
}

/**
 * Minimal Taskplus-style progress bar.
 */
const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(
  ({ className, value = 0, ...props }, ref) => {
    const clamped = Math.min(100, Math.max(0, value ?? 0));

    return (
      <div
        ref={ref}
        className={cn(
          "relative h-1.5 w-full overflow-hidden rounded-full bg-[hsl(var(--tp-sidebar))]",
          className,
        )}
        {...props}
      >
        <div
          className="h-full w-full rounded-full bg-[hsl(var(--tp-blue))] transition-transform duration-300 ease-out"
          style={{ transform: `translateX(-${100 - clamped}%)` }}
        />
      </div>
    );
  },
);

Progress.displayName = "Progress";

export { Progress };
