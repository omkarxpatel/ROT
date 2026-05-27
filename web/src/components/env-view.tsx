"use client";

import { useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";

import type { RotSnapshot } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface EnvViewProps {
  snapshot: RotSnapshot;
  // The snapshot from the previous step (or null if this is the first
  // step). Used to compute "new" / "changed" binding indicators and
  // the natural-language explainer copy.
  previousSnapshot?: RotSnapshot | null;
  // Bumped on each step. Used to re-key the explainer line so it
  // ticks over with an enter/exit transition between steps; frames
  // and binding rows stay stable so individual values can animate
  // (slot-machine style) without the whole panel re-flashing.
  stepKey: number;
}

export function EnvView({ snapshot, previousSnapshot, stepKey }: EnvViewProps) {
  const isError = Boolean(snapshot.error);
  const explanation = useMemo(
    () => explainSnapshot(snapshot, previousSnapshot ?? null),
    [snapshot, previousSnapshot],
  );

  return (
    <div className="space-y-3">
      <StatementHeader
        snapshot={snapshot}
        explanation={explanation}
        explanationKey={stepKey}
        isError={isError}
      />
      <div className="space-y-2">
        {snapshot.env.map((frame, i) => {
          const prevFrame = matchingFrame(previousSnapshot, frame);
          const changes = computeBindingChanges(
            frame.bindings,
            prevFrame?.bindings,
          );
          return (
            <motion.div
              key={`${frame.scope_label}-${i}`}
              layout
              transition={{ layout: { duration: 0.5, ease: "easeOut" } }}
              className="rounded-md border border-border/60 bg-background/40 p-2"
            >
              <div className="mb-1.5 flex items-center gap-2 text-[10.5px] uppercase tracking-wider text-muted-foreground">
                <span>{frame.scope_kind}</span>
                <span className="font-mono normal-case text-foreground/80">
                  {frame.scope_label}
                </span>
              </div>
              <Bindings bindings={frame.bindings} changes={changes} />
            </motion.div>
          );
        })}
      </div>
      {isError && (
        <motion.div
          key={`${stepKey}-err`}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, ease: "easeOut" }}
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
  explanation,
  explanationKey,
  isError,
}: {
  snapshot: RotSnapshot;
  explanation: string;
  explanationKey: number;
  isError: boolean;
}) {
  return (
    <div>
      <div className="relative h-6 overflow-hidden">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.div
            key={explanationKey}
            initial={{ y: 22, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -22, opacity: 0 }}
            transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
            className={cn(
              "absolute inset-0 flex items-center text-[14px] font-medium",
              isError ? "text-destructive" : "text-foreground/90",
            )}
          >
            {explanation}
          </motion.div>
        </AnimatePresence>
      </div>
      <div
        className={cn(
          "mt-0.5 text-[10.5px] text-muted-foreground",
          isError && "text-destructive/70",
        )}
      >
        <span className="opacity-70">after</span>{" "}
        <span className="font-mono">{snapshot.statement_kind}</span>{" "}
        <span className="opacity-60">
          at line {snapshot.statement_line}:{snapshot.statement_col}
        </span>
      </div>
    </div>
  );
}

interface BindingsProps {
  bindings: Record<string, string>;
  changes: Record<string, "new" | "changed">;
}

function Bindings({ bindings, changes }: BindingsProps) {
  const entries = Object.entries(bindings);
  if (entries.length === 0) {
    return (
      <div className="text-xs italic text-muted-foreground">(no bindings)</div>
    );
  }
  return (
    <div className="space-y-0.5 font-mono text-[12.5px]">
      <AnimatePresence initial={false} mode="popLayout">
        {entries.map(([name, value]) => (
          <BindingRow
            key={name}
            name={name}
            value={value}
            change={changes[name]}
          />
        ))}
      </AnimatePresence>
    </div>
  );
}

function BindingRow({
  name,
  value,
  change,
}: {
  name: string;
  value: string;
  change: "new" | "changed" | undefined;
}) {
  const dotClass =
    change === "new"
      ? "text-emerald-400"
      : change === "changed"
        ? "text-amber-400"
        : "text-transparent";
  const rowClass =
    change === "new"
      ? "bg-emerald-500/10 ring-1 ring-emerald-500/20"
      : change === "changed"
        ? "bg-amber-500/10 ring-1 ring-amber-500/20"
        : "ring-1 ring-transparent";
  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 12, scale: 0.96 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -12, scale: 0.96 }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className={cn(
        "flex items-baseline gap-2 rounded px-1.5 py-1 transition-[background-color,box-shadow] duration-700",
        rowClass,
      )}
      title={
        change === "new"
          ? "new binding in this step"
          : change === "changed"
            ? "value changed in this step"
            : undefined
      }
    >
      <span
        className={cn(
          "w-2 select-none text-base leading-none transition-colors duration-500",
          dotClass,
        )}
      >
        •
      </span>
      <span className="text-sky-400">{name}</span>
      <span className="text-zinc-500">=</span>
      <div className="relative min-h-[1.2em] flex-1 overflow-hidden">
        <AnimatePresence mode="popLayout" initial={false}>
          <motion.span
            key={value}
            initial={{ y: 20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: -20, opacity: 0 }}
            transition={{ duration: 0.55, ease: [0.16, 1, 0.3, 1] }}
            className="inline-block break-all text-emerald-300"
          >
            {value}
          </motion.span>
        </AnimatePresence>
      </div>
    </motion.div>
  );
}

// ─── Helpers ────────────────────────────────────────────────────────

function matchingFrame(
  prev: RotSnapshot | null | undefined,
  frame: { scope_kind: string; scope_label: string },
) {
  if (!prev) return null;
  return (
    prev.env.find(
      (f) =>
        f.scope_kind === frame.scope_kind && f.scope_label === frame.scope_label,
    ) ?? null
  );
}

function computeBindingChanges(
  current: Record<string, string>,
  previous: Record<string, string> | undefined,
): Record<string, "new" | "changed"> {
  if (!previous) {
    const out: Record<string, "new" | "changed"> = {};
    for (const k of Object.keys(current)) out[k] = "new";
    return out;
  }
  const out: Record<string, "new" | "changed"> = {};
  for (const [k, v] of Object.entries(current)) {
    if (!(k in previous)) out[k] = "new";
    else if (previous[k] !== v) out[k] = "changed";
  }
  return out;
}

function explainSnapshot(
  snap: RotSnapshot,
  prev: RotSnapshot | null,
): string {
  if (snap.error) return `Error during ${humanKind(snap.statement_kind)}.`;
  // Use the INNERMOST frame for diffing — that's where the just-
  // executed statement's changes live. Outside a function call that's
  // just the global; inside, it's the function/method/catch local.
  const frame = snap.env[snap.env.length - 1];
  const prevFrame = prev ? matchingFrame(prev, frame ?? { scope_kind: "", scope_label: "" }) : null;
  const changes = computeBindingChanges(frame?.bindings ?? {}, prevFrame?.bindings);
  const newKeys = Object.entries(changes)
    .filter(([, c]) => c === "new")
    .map(([k]) => k);
  const changedKeys = Object.entries(changes)
    .filter(([, c]) => c === "changed")
    .map(([k]) => k);
  const output = snap.output_since_last;
  const out = output ? quoteShort(output) : "";

  switch (snap.statement_kind) {
    case "Assign":
    case "LetStmt": {
      const key = newKeys[0] ?? changedKeys[0];
      if (key) {
        const value = frame.bindings[key];
        const verb = newKeys.includes(key) ? "Bound" : "Rebound";
        return `${verb} ${key} = ${value}.`;
      }
      return "Assignment evaluated.";
    }
    case "IndexAssign":
      return "Index assignment evaluated.";
    case "MemberAssign":
      return "Field assignment evaluated.";
    case "ExprStmt":
      if (output) return `Evaluated expression. Printed ${out}.`;
      return "Evaluated expression.";
    case "IfStmt":
      if (changedKeys.length === 1)
        return `Conditional taken; ${changedKeys[0]} updated.`;
      if (newKeys.length === 1)
        return `Conditional taken; ${newKeys[0]} bound.`;
      return "Conditional taken.";
    case "WhileStmt":
      if (output) return `Loop ran; printed ${out}.`;
      return "Loop ran to completion.";
    case "ForStmt":
      if (output) return `For loop iterated; printed ${out}.`;
      return "For loop iterated.";
    case "FuncDef":
      return `Defined funct ${newKeys[0] ?? "<anon>"}.`;
    case "ClassDef":
      return `Defined class ${newKeys[0] ?? "<anon>"}.`;
    case "Return":
      return "Return outside a function — no-op at the top level.";
    case "TryCatch":
      if (output) return `try/catch ran; printed ${out}.`;
      return "try/catch ran.";
    case "ThrowStmt":
      return "Threw a value.";
    case "ImportStmt":
      return "Imported module.";
    case "BreakStmt":
    case "ContinueStmt":
      return `${snap.statement_kind} reached top-level — unusual.`;
    default:
      if (output) return `${humanKind(snap.statement_kind)}; printed ${out}.`;
      return `Executed ${humanKind(snap.statement_kind)}.`;
  }
}

function humanKind(kind: string): string {
  const map: Record<string, string> = {
    Assign: "assignment",
    LetStmt: "let-binding",
    ExprStmt: "expression statement",
    IfStmt: "if statement",
    WhileStmt: "while loop",
    ForStmt: "for loop",
    FuncDef: "function definition",
    ClassDef: "class definition",
    Return: "return",
    TryCatch: "try/catch",
    ThrowStmt: "throw",
    ImportStmt: "import",
  };
  return map[kind] ?? kind;
}

function quoteShort(s: string): string {
  const trimmed = s.replace(/\n+$/, "");
  const inline = trimmed.replace(/\n/g, "\\n");
  const cap = 40;
  if (inline.length <= cap) return JSON.stringify(inline);
  return JSON.stringify(inline.slice(0, cap)) + "…";
}
