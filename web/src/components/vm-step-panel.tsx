"use client";

import { AnimatePresence, motion } from "framer-motion";
import { ArrowDown, ArrowUp, Layers, Terminal } from "lucide-react";

import type { RotVMSnapshot } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface VMStepPanelProps {
  snapshot: RotVMSnapshot | null;
  previousSnapshot: RotVMSnapshot | null;
  stepIndex: number;
  totalSteps: number;
  chunkId: string;
}

// VM-mode equivalent of the tree-walker's StepPanel. Renders the
// active opcode, an animated stack, and the env diff. Bytecode pane
// (separate component below the panel) shows the chunk-level IP
// marker.

export function VMStepPanel({
  snapshot,
  previousSnapshot,
  stepIndex,
  totalSteps,
  chunkId,
}: VMStepPanelProps) {
  if (!snapshot) {
    return (
      <div className="flex h-full items-center justify-center p-6 text-sm text-muted-foreground">
        Press{" "}
        <span className="mx-1 font-mono text-foreground/80">Step</span> or{" "}
        <span className="mx-1 font-mono text-foreground/80">Play</span> to
        run this program through the bytecode VM.
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <div className="flex items-center justify-between border-b border-amber-500/20 px-3 py-2">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider">
          <Layers className="h-3 w-3 text-amber-300" />
          <span className="text-amber-300">VM step</span>
          <span className="text-muted-foreground">·</span>
          <span className="font-mono normal-case text-foreground/80">
            chunk: {chunkId}
          </span>
          {snapshot.frame_depth > 0 && (
            <>
              <span className="text-muted-foreground">·</span>
              <span className="normal-case text-foreground/70">
                frame depth {snapshot.frame_depth}
              </span>
            </>
          )}
        </div>
        <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
          {stepIndex + 1} / {totalSteps}
        </span>
      </div>
      <div className="flex-1 overflow-auto p-3">
        <OpcodeRow snapshot={snapshot} />
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <StackCard
            snapshot={snapshot}
            previousSnapshot={previousSnapshot}
          />
          <EnvCard
            snapshot={snapshot}
            previousSnapshot={previousSnapshot}
          />
        </div>
        {snapshot.output_since_last && (
          <OutputRow text={snapshot.output_since_last} />
        )}
        {snapshot.error && <ErrorRow message={snapshot.error} />}
      </div>
    </div>
  );
}

function OpcodeRow({ snapshot }: { snapshot: RotVMSnapshot }) {
  return (
    <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
        executed
      </div>
      <div className="mt-1 flex items-baseline gap-2 font-mono">
        <span className="text-[10px] text-muted-foreground/70 tabular-nums">
          {String(snapshot.prev_ip).padStart(3, "0")}
        </span>
        <span className="text-base font-semibold text-amber-200">
          {snapshot.op_name}
        </span>
        {snapshot.op_args.length > 0 && (
          <span className="text-sm text-foreground/70">
            {snapshot.op_args.map(String).join(" ")}
          </span>
        )}
        {snapshot.line > 0 && (
          <span className="ml-auto text-[10px] uppercase tracking-wider text-muted-foreground">
            line {snapshot.line}
          </span>
        )}
      </div>
    </div>
  );
}

function StackCard({
  snapshot,
  previousSnapshot,
}: {
  snapshot: RotVMSnapshot;
  previousSnapshot: RotVMSnapshot | null;
}) {
  const prevStack = previousSnapshot?.stack ?? [];
  const curStack = snapshot.stack;
  const delta = curStack.length - prevStack.length;

  return (
    <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Stack
        </span>
        <span className="flex items-center gap-1 text-[10px] text-muted-foreground/70">
          {delta > 0 && (
            <>
              <ArrowUp className="h-3 w-3 text-emerald-300" />
              <span className="text-emerald-300">+{delta}</span>
            </>
          )}
          {delta < 0 && (
            <>
              <ArrowDown className="h-3 w-3 text-rose-300" />
              <span className="text-rose-300">{delta}</span>
            </>
          )}
        </span>
      </div>
      {/* Top of stack at the top of the visual — feels right for
          push/pop. Each entry framer-motion's into place. */}
      <div className="flex min-h-[3rem] flex-col-reverse gap-1">
        <AnimatePresence>
          {curStack.map((v, i) => (
            <motion.div
              key={`${i}-${v}`}
              initial={{ opacity: 0, y: -8, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -8, scale: 0.9 }}
              transition={{ duration: 0.16 }}
              className={cn(
                "rounded border px-2 py-0.5 text-center font-mono text-[11.5px] tabular-nums",
                i === curStack.length - 1
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-100"
                  : "border-border/60 bg-background/60 text-foreground/70",
              )}
            >
              {v}
            </motion.div>
          ))}
        </AnimatePresence>
        {curStack.length === 0 && (
          <span className="text-[10px] uppercase tracking-wider text-muted-foreground/40">
            empty
          </span>
        )}
      </div>
    </div>
  );
}

function EnvCard({
  snapshot,
  previousSnapshot,
}: {
  snapshot: RotVMSnapshot;
  previousSnapshot: RotVMSnapshot | null;
}) {
  // Show locals (when inside a function) first, then globals. Highlight
  // any binding that changed vs. the previous snapshot.
  const prevLocals = previousSnapshot?.locals_view ?? {};
  const prevGlobals = previousSnapshot?.globals_view ?? {};
  const localsEntries = Object.entries(snapshot.locals_view);
  const globalsEntries = Object.entries(snapshot.globals_view);

  if (localsEntries.length === 0 && globalsEntries.length === 0) {
    return (
      <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Env
        </div>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground/40">
          empty
        </span>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border/60 bg-background/40 px-3 py-2">
      <div className="mb-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        Env
      </div>
      <div className="space-y-1">
        {localsEntries.length > 0 && (
          <div>
            <div className="mb-0.5 text-[9px] uppercase tracking-wider text-amber-300/80">
              locals
            </div>
            {localsEntries.map(([k, v]) => (
              <BindingRow
                key={`l-${k}`}
                name={k}
                value={v}
                changed={prevLocals[k] !== v}
              />
            ))}
          </div>
        )}
        {globalsEntries.length > 0 && (
          <div>
            <div className="mb-0.5 mt-1 text-[9px] uppercase tracking-wider text-sky-300/80">
              globals
            </div>
            {globalsEntries.map(([k, v]) => (
              <BindingRow
                key={`g-${k}`}
                name={k}
                value={v}
                changed={prevGlobals[k] !== v}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function BindingRow({
  name,
  value,
  changed,
}: {
  name: string;
  value: string;
  changed: boolean;
}) {
  return (
    <div
      className={cn(
        "flex items-baseline gap-2 rounded px-1 py-0.5 font-mono text-[11.5px] transition-colors",
        changed && "bg-amber-500/10",
      )}
    >
      <span className="text-sky-300">{name}</span>
      <span className="text-muted-foreground">=</span>
      <motion.span
        key={value}
        initial={changed ? { opacity: 0, y: -4 } : false}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.18 }}
        className="text-foreground tabular-nums"
      >
        {value}
      </motion.span>
    </div>
  );
}

function OutputRow({ text }: { text: string }) {
  return (
    <div className="mt-3 rounded-md border border-emerald-500/30 bg-emerald-500/5 px-3 py-2">
      <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-emerald-300">
        <Terminal className="h-3 w-3" />
        <span>print</span>
      </div>
      <pre className="whitespace-pre-wrap font-mono text-[12px] text-foreground">
        {text}
      </pre>
    </div>
  );
}

function ErrorRow({ message }: { message: string }) {
  return (
    <div className="mt-3 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2">
      <div className="text-[10px] uppercase tracking-wider text-destructive">
        error
      </div>
      <div className="mt-1 font-mono text-[12px] text-destructive/90">
        {message}
      </div>
    </div>
  );
}
