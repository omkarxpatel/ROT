"use client";

import { Fragment } from "react";
import { motion } from "framer-motion";

import type { RotSnapshot } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface EnvViewProps {
  snapshot: RotSnapshot;
  // Bumped on each step so newly-changed bindings can animate. Read by
  // the consumer to decide when to re-mount; the view itself just
  // renders the current state.
  stepKey: number;
}

export function EnvView({ snapshot, stepKey }: EnvViewProps) {
  const isError = Boolean(snapshot.error);
  return (
    <div className="space-y-2">
      <StatementHeader snapshot={snapshot} isError={isError} />
      {snapshot.env.map((frame, i) => (
        <motion.div
          // Re-mount per step so the per-frame fade-in animates each
          // time the user clicks Step.
          key={`${stepKey}-${i}`}
          initial={{ opacity: 0, y: 2 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.16, delay: i * 0.04 }}
          className={cn(
            "rounded-md border border-border/60 bg-background/40 p-2",
          )}
        >
          <div className="mb-1.5 flex items-center gap-2 text-[10.5px] uppercase tracking-wider text-muted-foreground">
            <span>{frame.scope_kind}</span>
            <span className="font-mono normal-case text-foreground/80">
              {frame.scope_label}
            </span>
          </div>
          <Bindings bindings={frame.bindings} />
        </motion.div>
      ))}
      {isError && (
        <motion.div
          key={`${stepKey}-err`}
          initial={{ opacity: 0, y: 2 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18 }}
          className="rounded-md border border-destructive/40 bg-destructive/10 p-2 text-[12.5px] text-destructive"
        >
          <div className="mb-1 text-[10px] font-semibold uppercase tracking-wider">
            error
          </div>
          <pre className="whitespace-pre-wrap break-words font-mono">
            {snapshot.error}
          </pre>
        </motion.div>
      )}
    </div>
  );
}

function StatementHeader({
  snapshot,
  isError,
}: {
  snapshot: RotSnapshot;
  isError: boolean;
}) {
  return (
    <div
      className={cn(
        "text-[11px] text-muted-foreground",
        isError && "text-destructive/80",
      )}
    >
      <span className="opacity-70">After:</span>{" "}
      <span className="font-mono text-foreground/80">
        {snapshot.statement_kind}
      </span>{" "}
      <span className="opacity-60">
        at line {snapshot.statement_line}:{snapshot.statement_col}
      </span>
    </div>
  );
}

function Bindings({ bindings }: { bindings: Record<string, string> }) {
  const entries = Object.entries(bindings);
  if (entries.length === 0) {
    return (
      <div className="text-xs italic text-muted-foreground">(no bindings)</div>
    );
  }
  return (
    <div className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 font-mono text-[12.5px]">
      {entries.map(([name, value]) => (
        <Fragment key={name}>
          <span className="text-sky-400">{name}</span>
          <span className="break-all text-emerald-300">{value}</span>
        </Fragment>
      ))}
    </div>
  );
}
