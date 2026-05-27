"use client";

import { useEffect, useRef } from "react";

import type { RotSnapshot } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface SnapshotTimelineProps {
  snapshots: RotSnapshot[];
  stepIndex: number;
  onStepChange: (next: number) => void;
}

// A horizontal strip of dots, one per snapshot. Past = faded amber,
// current = bright amber with a ring, future = neutral, error = red.
// Click any dot to jump to that step. Auto-scrolls the current dot
// into view so you don't lose it on long programs.
export function SnapshotTimeline({
  snapshots,
  stepIndex,
  onStepChange,
}: SnapshotTimelineProps) {
  const activeRef = useRef<HTMLButtonElement | null>(null);

  useEffect(() => {
    activeRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "nearest",
      inline: "center",
    });
  }, [stepIndex]);

  if (snapshots.length === 0) {
    return (
      <div className="px-3 py-2 text-xs text-muted-foreground">
        Click <span className="font-mono text-foreground/80">Step</span> or{" "}
        <span className="font-mono text-foreground/80">Play</span> to populate
        the timeline.
      </div>
    );
  }

  return (
    <div className="px-3 py-2">
      <div className="mb-1 flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
        <span>Timeline</span>
        <span className="font-mono normal-case">
          {snapshots.length} snapshot{snapshots.length === 1 ? "" : "s"}
        </span>
      </div>
      <div className="overflow-x-auto">
        <div className="flex items-center gap-[2px] py-1">
          {snapshots.map((snap, i) => {
            const isActive = i === stepIndex;
            const isPast = i < stepIndex;
            const hasError = Boolean(snap.error);
            return (
              <button
                key={i}
                ref={isActive ? activeRef : null}
                onClick={() => onStepChange(i)}
                title={`Step ${i + 1}: ${snap.statement_kind} at line ${snap.statement_line}:${snap.statement_col}${hasError ? " — error" : ""}`}
                className={cn(
                  "h-5 w-[6px] flex-shrink-0 rounded-sm transition-all hover:scale-110",
                  hasError && isActive && "bg-red-400 ring-2 ring-red-300",
                  hasError && !isActive && "bg-red-500/60",
                  !hasError && isActive &&
                    "scale-110 bg-amber-400 ring-2 ring-amber-300",
                  !hasError && !isActive && isPast && "bg-amber-500/55",
                  !hasError && !isActive && !isPast &&
                    "bg-zinc-600 hover:bg-zinc-500",
                )}
                aria-label={`Jump to step ${i + 1}`}
              />
            );
          })}
        </div>
      </div>
    </div>
  );
}
