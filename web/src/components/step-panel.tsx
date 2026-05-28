"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertOctagon,
  ArrowDown,
  Check,
  ChevronRight,
  Code2,
  FileCode2,
  Layers,
  Repeat,
  Sparkles,
} from "lucide-react";

import { EnvView } from "@/components/env-view";
import { ScrollArea } from "@/components/ui/scroll-area";
import { StructureView } from "@/components/structure-view";
import { tokenTextColor } from "@/components/tokens-view";
import type {
  AstNode,
  AstValue,
  RotSnapshot,
  RotToken,
} from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface StepPanelProps {
  source: string;
  tokens: RotToken[];
  ast: AstNode | null;
  snapshot: RotSnapshot | null;
  previousSnapshot: RotSnapshot | null;
  stepIndex: number;
  totalSteps: number;
  // When the user clicks a token chip, the playground jumps the
  // editor cursor to that source position.
  onJumpToSource?: (line: number, col: number) => void;
  // Play mode + speed. When playing, animations compress so the
  // staged reveals all fit inside the user's chosen step interval.
  playing?: boolean;
  speedMs?: number;
}

// Three phases now: READ (source line with colors) → PARSE
// (pretty-printed structure) → RUN (env + output). The v2.26.x
// Tokens chip strip and the dense AST tree have been replaced.
const STAGE_DELAYS_BASE = {
  read: 0,
  parse: 0.18,
  run: 0.55,
};
const NATURAL_TOTAL_MS = 1000;

export function StepPanel({
  source,
  tokens,
  ast,
  snapshot,
  previousSnapshot,
  stepIndex,
  totalSteps,
  onJumpToSource,
  playing = false,
  speedMs,
}: StepPanelProps) {
  const hasSteps = totalSteps > 0;
  const progressPct = hasSteps
    ? Math.round(((stepIndex + 1) / totalSteps) * 100)
    : 0;
  const isAtEnd = hasSteps && stepIndex === totalSteps - 1;
  const endedOnError = isAtEnd && Boolean(snapshot?.error);
  const animScale =
    playing && typeof speedMs === "number"
      ? Math.max(0.2, Math.min(1, speedMs / NATURAL_TOTAL_MS))
      : 1;

  // Scroll the Step Detail panel back to the top on every step
  // change. Without this, if the user manually scrolled down to
  // peek at the Run stage and then let Play continue, the panel
  // would stay scrolled down — they'd never see Read / Parse on
  // the next snapshot. Reach into Radix's ScrollArea viewport via
  // the data-attribute Radix tags it with.
  const scrollAreaRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const viewport = scrollAreaRef.current?.querySelector<HTMLElement>(
      "[data-radix-scroll-area-viewport]",
    );
    viewport?.scrollTo({ top: 0, behavior: "smooth" });
  }, [stepIndex]);

  return (
    <div className="flex h-full flex-col">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1 border-b border-border/60 px-3 py-2">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
            <Sparkles className="h-3.5 w-3.5 text-amber-400" />
            <span>Step Detail</span>
          </div>
          {snapshot && <CallBreadcrumb snapshot={snapshot} />}
          {snapshot && snapshot.loop_iter != null && (
            <LoopIterBadge
              iter={snapshot.loop_iter}
              total={snapshot.loop_total}
            />
          )}
        </div>
        {hasSteps && stepIndex >= 0 && (
          <div className="flex items-center gap-2">
            <span className="font-mono text-[11px] tabular-nums text-muted-foreground">
              step {stepIndex + 1}/{totalSteps}
            </span>
            <div className="h-1 w-24 overflow-hidden rounded-full bg-border/60">
              <div
                className={cn(
                  "h-full transition-[width] duration-500 ease-out",
                  endedOnError
                    ? "bg-red-500"
                    : isAtEnd
                      ? "bg-emerald-400"
                      : "bg-amber-400/80",
                )}
                style={{ width: `${progressPct}%` }}
              />
            </div>
            {isAtEnd && endedOnError && (
              <motion.span
                key="halted"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="inline-flex items-center gap-1 rounded-full border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-red-300"
                title="Program halted on an error — see the Run phase for details."
              >
                <AlertOctagon className="h-3 w-3" />
                halted
              </motion.span>
            )}
            {isAtEnd && !endedOnError && (
              <motion.span
                key="done"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="inline-flex items-center gap-1 rounded-full border border-emerald-500/40 bg-emerald-500/10 px-2 py-0.5 text-[10.5px] font-semibold uppercase tracking-wider text-emerald-300"
                title="Program finished — no more steps."
              >
                <Check className="h-3 w-3" />
                done
              </motion.span>
            )}
          </div>
        )}
      </div>
      <ScrollArea ref={scrollAreaRef} className="min-h-0 flex-1">
        <div className="p-3">
          {snapshot ? (
            <StagedView
              source={source}
              tokens={tokens}
              ast={ast}
              snapshot={snapshot}
              previousSnapshot={previousSnapshot}
              stepIndex={stepIndex}
              onJumpToSource={onJumpToSource}
              animScale={animScale}
            />
          ) : (
            <OnboardingMessage />
          )}
        </div>
      </ScrollArea>
    </div>
  );
}

function StagedView({
  source,
  tokens,
  ast,
  snapshot,
  previousSnapshot,
  stepIndex,
  onJumpToSource,
  animScale,
}: {
  source: string;
  tokens: RotToken[];
  ast: AstNode | null;
  snapshot: RotSnapshot;
  previousSnapshot: RotSnapshot | null;
  stepIndex: number;
  onJumpToSource?: (line: number, col: number) => void;
  animScale: number;
}) {
  const stmtLine = snapshot.statement_line;
  const stmtCol = snapshot.statement_col;

  const lineText = useMemo(() => {
    const lines = source.split("\n");
    return lines[stmtLine - 1] ?? "";
  }, [source, stmtLine]);

  const stmtAst = useMemo<AstNode | null>(
    () =>
      findStatementAst(ast, stmtLine, stmtCol, snapshot.statement_kind),
    [ast, stmtLine, stmtCol, snapshot.statement_kind],
  );

  const STAGE_DELAYS = {
    read: STAGE_DELAYS_BASE.read * animScale,
    parse: STAGE_DELAYS_BASE.parse * animScale,
    run: STAGE_DELAYS_BASE.run * animScale,
  };

  return (
    <div className="space-y-3">
      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.read}
        icon={<FileCode2 className="h-3.5 w-3.5" />}
        title="Read"
        subtitle={`line ${stmtLine}:${stmtCol}`}
      >
        <SourceLine
          line={lineText}
          col={stmtCol}
          tokens={tokens}
          lineNumber={stmtLine}
          onClickToken={onJumpToSource}
        />
      </StageBlock>

      <StageArrow stepIndex={stepIndex} delaySec={STAGE_DELAYS.parse - 0.05} />

      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.parse}
        icon={<Code2 className="h-3.5 w-3.5" />}
        title="Parse"
        subtitle={stmtAst?.__type__ ?? snapshot.statement_kind}
      >
        <StructureView
          ast={stmtAst}
          stepKey={stepIndex}
          baseDelaySec={STAGE_DELAYS.parse + 0.05}
        />
      </StageBlock>

      <StageArrow stepIndex={stepIndex} delaySec={STAGE_DELAYS.run - 0.05} />

      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.run}
        icon={<Layers className="h-3.5 w-3.5" />}
        title="Run"
        subtitle={snapshot.error ? "error" : "env updated"}
        accent={snapshot.error ? "error" : "exec"}
      >
        <ExecBlock
          snapshot={snapshot}
          previousSnapshot={previousSnapshot}
          stepIndex={stepIndex}
          execDelaySec={STAGE_DELAYS.run}
        />
      </StageBlock>
    </div>
  );
}

function StageBlock({
  stepIndex,
  delaySec,
  icon,
  title,
  subtitle,
  accent,
  children,
}: {
  stepIndex: number;
  delaySec: number;
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  accent?: "error" | "exec";
  children: React.ReactNode;
}) {
  return (
    <motion.div
      key={`${stepIndex}-${title}`}
      initial={{ opacity: 0, y: 10, scale: 0.99 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        delay: delaySec,
        duration: 0.4,
        ease: [0.16, 1, 0.3, 1],
      }}
      className={cn(
        "rounded-md border bg-background/40 p-2.5",
        accent === "error"
          ? "border-destructive/40"
          : accent === "exec"
            ? "border-emerald-500/30"
            : "border-border/60",
      )}
    >
      <div
        className={cn(
          "mb-1.5 flex items-center justify-between gap-2 text-[11px] font-semibold uppercase tracking-wider",
          accent === "error" ? "text-destructive/80" : "text-muted-foreground",
        )}
      >
        <span className="flex items-center gap-1.5">
          {icon}
          <span>{title}</span>
        </span>
        {subtitle && (
          <span className="font-mono text-[10px] font-normal normal-case text-foreground/60">
            {subtitle}
          </span>
        )}
      </div>
      {children}
    </motion.div>
  );
}

function StageArrow({
  stepIndex,
  delaySec,
}: {
  stepIndex: number;
  delaySec: number;
}) {
  return (
    <motion.div
      key={`${stepIndex}-arrow-${delaySec}`}
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 0.5, y: 0 }}
      transition={{ delay: delaySec, duration: 0.3 }}
      className="flex justify-center"
    >
      <ArrowDown className="h-3.5 w-3.5 text-muted-foreground" />
    </motion.div>
  );
}

function SourceLine({
  line,
  col,
  tokens,
  lineNumber,
  onClickToken,
}: {
  line: string;
  col: number;
  tokens: RotToken[];
  lineNumber: number;
  onClickToken?: (line: number, col: number) => void;
}) {
  const segments = useMemo(
    () => splitLineByTokens(line, tokens, lineNumber),
    [line, tokens, lineNumber],
  );
  if (line.length === 0) {
    return (
      <pre className="rounded bg-zinc-900/60 px-3 py-2 font-mono text-[13px] text-muted-foreground">
        (empty line)
      </pre>
    );
  }
  return (
    <div className="space-y-0.5">
      <pre className="overflow-x-auto whitespace-pre rounded bg-zinc-900/60 px-3 py-2 font-mono text-[13px]">
        {segments.map((seg, i) =>
          seg.kind ? (
            <span
              key={i}
              className={cn(
                tokenTextColor(seg.kind),
                onClickToken &&
                  "cursor-pointer underline-offset-2 hover:underline",
              )}
              onClick={
                onClickToken && seg.line
                  ? () => onClickToken(seg.line!, seg.col!)
                  : undefined
              }
              title={
                onClickToken
                  ? `${seg.kind.toLowerCase()} — click to jump`
                  : seg.kind.toLowerCase()
              }
            >
              {seg.text}
            </span>
          ) : (
            <span key={i} className="text-foreground/40">
              {seg.text}
            </span>
          ),
        )}
      </pre>
      {col >= 1 && col <= line.length + 1 && (
        <pre
          aria-hidden
          className="overflow-x-auto whitespace-pre px-3 font-mono text-[10px] text-amber-400/80"
        >
          {" ".repeat(col - 1)}^
        </pre>
      )}
    </div>
  );
}

interface SourceSeg {
  text: string;
  kind: string | null;
  line?: number;
  col?: number;
}

function splitLineByTokens(
  line: string,
  tokens: RotToken[],
  lineNumber: number,
): SourceSeg[] {
  const onLine = tokens
    .filter((t) => t.line === lineNumber)
    .sort((a, b) => a.col - b.col);
  if (onLine.length === 0) {
    return [{ text: line, kind: null }];
  }
  const out: SourceSeg[] = [];
  let cursor = 0;
  for (const tok of onLine) {
    const start = Math.max(0, tok.col - 1);
    if (start > cursor) {
      out.push({ text: line.slice(cursor, start), kind: null });
    }
    const end = Math.min(line.length, start + tok.lexeme.length);
    if (end > start) {
      out.push({
        text: line.slice(start, end),
        kind: tok.kind,
        line: tok.line,
        col: tok.col,
      });
    }
    cursor = Math.max(cursor, end);
  }
  if (cursor < line.length) {
    out.push({ text: line.slice(cursor), kind: null });
  }
  return out;
}

function ExecBlock({
  snapshot,
  previousSnapshot,
  stepIndex,
  execDelaySec,
}: {
  snapshot: RotSnapshot;
  previousSnapshot: RotSnapshot | null;
  stepIndex: number;
  execDelaySec: number;
}) {
  return (
    <div className="space-y-2">
      {snapshot.output_since_last && (
        <motion.div
          key={`${stepIndex}-out`}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            delay: execDelaySec + 0.1,
            duration: 0.4,
            ease: "easeOut",
          }}
          className="rounded border border-border/60 bg-zinc-900/60 px-2 py-1.5"
        >
          <div className="mb-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
            printed
          </div>
          <pre className="whitespace-pre-wrap break-words font-mono text-[12.5px] text-emerald-300">
            {snapshot.output_since_last}
          </pre>
        </motion.div>
      )}
      <EnvView
        snapshot={snapshot}
        previousSnapshot={previousSnapshot}
        stepKey={stepIndex}
      />
    </div>
  );
}

function CallBreadcrumb({ snapshot }: { snapshot: RotSnapshot }) {
  if (snapshot.env.length === 0) return null;
  const isLast = (i: number) => i === snapshot.env.length - 1;
  return (
    <div className="flex items-center gap-1 overflow-hidden">
      <AnimatePresence mode="popLayout" initial={false}>
        {snapshot.env.flatMap((frame, i) => {
          const key = `${frame.scope_label}-${i}`;
          const items: React.ReactNode[] = [];
          if (i > 0) {
            items.push(
              <motion.span
                key={`sep-${key}`}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 0.5, x: 0 }}
                exit={{ opacity: 0, x: -4 }}
                transition={{ duration: 0.25 }}
                className="text-muted-foreground"
                aria-hidden
              >
                <ChevronRight className="h-3 w-3" />
              </motion.span>,
            );
          }
          items.push(
            <motion.span
              key={`pill-${key}`}
              layout
              initial={{ opacity: 0, x: 12, scale: 0.94 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 12, scale: 0.94 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className={cn(
                "rounded-full border px-2 py-0.5 font-mono text-[10.5px]",
                isLast(i)
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                  : "border-border/60 bg-background/40 text-muted-foreground",
              )}
            >
              {frame.scope_label}
            </motion.span>,
          );
          return items;
        })}
      </AnimatePresence>
    </div>
  );
}

function LoopIterBadge({
  iter,
  total,
}: {
  iter: number;
  total: number | null;
}) {
  return (
    <motion.span
      key={`loop-${iter}-${total ?? "?"}`}
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      className="inline-flex items-center gap-1 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10.5px] text-cyan-300"
      title={
        total != null
          ? `Loop iteration ${iter} of ${total}`
          : `Loop iteration ${iter} (total unknown — while loop)`
      }
    >
      <Repeat className="h-3 w-3" />
      iter {iter}
      {total != null && `/${total}`}
    </motion.span>
  );
}

function OnboardingMessage() {
  return (
    <div className="space-y-3 text-xs leading-relaxed text-muted-foreground">
      <p>
        Click <span className="font-mono text-foreground/80">Step</span> (or{" "}
        <span className="font-mono text-foreground/80">Play</span>) to start.
        Each click advances the interpreter one statement.
      </p>
      <p>For each statement, three phases:</p>
      <ol className="space-y-1 pl-4 [list-style:decimal]">
        <li>
          <span className="text-foreground/80">Read</span> — the line of source
          that just ran.
        </li>
        <li>
          <span className="text-foreground/80">Parse</span> — the parsed form
          shown as normalized code so nested structure is legible.
        </li>
        <li>
          <span className="text-foreground/80">Run</span> — what changed in the
          environment, what was printed, any errors.
        </li>
      </ol>
    </div>
  );
}

// ─── Statement-scoped AST lookup ────────────────────────────────

function findStatementAst(
  ast: AstNode | null,
  line: number,
  col: number,
  kind: string,
): AstNode | null {
  if (!ast) return null;
  let result: AstNode | null = null;
  function visit(v: AstValue): void {
    if (result) return;
    if (v === null || v === undefined) return;
    if (typeof v !== "object") return;
    if (Array.isArray(v)) {
      for (const x of v) visit(x);
      return;
    }
    const n = v as AstNode;
    const nl = typeof n.line === "number" ? n.line : 0;
    const nc = typeof n.col === "number" ? n.col : 0;
    if (n.__type__ === kind && nl === line && nc === col) {
      result = n;
      return;
    }
    for (const [k, child] of Object.entries(n)) {
      if (k === "__type__" || k === "line" || k === "col") continue;
      visit(child as AstValue);
    }
  }
  visit(ast);
  return result;
}
