"use client";

import { Layers } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import { EnvView } from "@/components/env-view";
import type { RotSnapshot } from "@/lib/pyodide-runtime";

interface EnvPanelProps {
  snapshot: RotSnapshot | null;
  previousSnapshot: RotSnapshot | null;
  stepIndex: number;
  totalSteps: number;
}

// Promoted from a buried accordion item to its own row in animate
// mode. Header carries a step counter + progress bar so each Step /
// Play tick reads as concrete forward motion.
export function EnvPanel({
  snapshot,
  previousSnapshot,
  stepIndex,
  totalSteps,
}: EnvPanelProps) {
  const hasSteps = totalSteps > 0;
  const progressPct = hasSteps
    ? Math.round(((stepIndex + 1) / totalSteps) * 100)
    : 0;
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between gap-3 border-b border-border/60 px-3 py-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
          <Layers className="h-3.5 w-3.5" />
          <span>Env</span>
        </div>
        {hasSteps && stepIndex >= 0 && (
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
              step {stepIndex + 1}/{totalSteps}
            </span>
            <div className="h-1 w-24 overflow-hidden rounded-full bg-border/60">
              <div
                className="h-full bg-amber-400/80 transition-[width] duration-500 ease-out"
                style={{ width: `${progressPct}%` }}
              />
            </div>
          </div>
        )}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-3">
          {snapshot ? (
            <EnvView
              snapshot={snapshot}
              previousSnapshot={previousSnapshot}
              stepKey={stepIndex}
            />
          ) : (
            <div className="text-xs leading-relaxed text-muted-foreground">
              <p className="mb-2">
                Click <span className="font-mono text-foreground/80">Step</span>{" "}
                (or <span className="font-mono text-foreground/80">Play</span>)
                to start animating execution.
              </p>
              <p>
                Each click advances the interpreter one top-level
                statement. As you step, you&apos;ll see the current line
                highlighted in the editor, the env pane fill in with
                colored indicators (emerald = new binding, amber =
                changed value), and a short explainer summarizing what
                just happened.
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
