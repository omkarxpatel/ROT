"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown,
  ChevronRight,
  Code2,
  ListTree,
  Repeat,
  Sparkles,
  Terminal,
} from "lucide-react";

import { AstView, type AstPulse } from "@/components/ast-view";
import { EnvView } from "@/components/env-view";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TokensView, tokenTextColor } from "@/components/tokens-view";
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
}

// Stage timing (seconds). The four reveals stagger so the user reads
// the pipeline left-to-right per step: source line → tokens → AST →
// execution effects. Each stage's `key` is the stepIndex so Step or
// Play re-fires the whole sequence on every advance.
const STAGE_DELAYS = {
  source: 0,
  tokens: 0.15,
  ast: 0.45,
  exec: 0.9,
};

export function StepPanel({
  source,
  tokens,
  ast,
  snapshot,
  previousSnapshot,
  stepIndex,
  totalSteps,
}: StepPanelProps) {
  const hasSteps = totalSteps > 0;
  const progressPct = hasSteps
    ? Math.round(((stepIndex + 1) / totalSteps) * 100)
    : 0;

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
            <StagedView
              source={source}
              tokens={tokens}
              ast={ast}
              snapshot={snapshot}
              previousSnapshot={previousSnapshot}
              stepIndex={stepIndex}
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
}: {
  source: string;
  tokens: RotToken[];
  ast: AstNode | null;
  snapshot: RotSnapshot;
  previousSnapshot: RotSnapshot | null;
  stepIndex: number;
}) {
  const stmtLine = snapshot.statement_line;
  const stmtCol = snapshot.statement_col;

  // 1) The source line text — what the user wrote on that row.
  const lineText = useMemo(() => {
    const lines = source.split("\n");
    return lines[stmtLine - 1] ?? "";
  }, [source, stmtLine]);

  // 2) The tokens on this statement (and any tokens whose line falls
  // within the statement's AST line range, catching multi-line
  // statements like funct definitions).
  const stmtTokens = useMemo(() => {
    return tokensForStatement(
      tokens,
      ast,
      stmtLine,
      stmtCol,
      snapshot.statement_kind,
    );
  }, [tokens, ast, stmtLine, stmtCol, snapshot.statement_kind]);

  // 3) The AST subtree for this snapshot's statement. With deep
  // stepping (v2.26.13) the snapshot stream contains nested
  // statements, so `body[stepIndex]` is wrong — that mapping only
  // worked when every snapshot was a top-level statement. Look up
  // by (line, col, kind) instead: walk the AST and return the first
  // node whose source position and AST type match.
  const stmtAst = useMemo<AstNode | null>(() => {
    return findStatementAst(ast, stmtLine, stmtCol, snapshot.statement_kind);
  }, [ast, stmtLine, stmtCol, snapshot.statement_kind]);

  // Token pulses: an AST leaf's entrance animation triggers a pulse
  // on the matching source token chip — closing the lex → parse
  // visual link.
  const [tokenPulses, setTokenPulses] = useState<Record<number, number>>({});
  const tokenPulseCounter = useRef(0);
  // AST pulses: when env adds a new/changed binding, the AST node
  // that produced it pulses — closing the parse → execute visual
  // link. Keyed by `${line}:${col}`.
  const [astPulses, setAstPulses] = useState<Record<string, AstPulse>>({});
  const astPulseCounter = useRef(0);
  // Reset both maps on each step.
  useEffect(() => {
    setTokenPulses({});
    setAstPulses({});
    tokenPulseCounter.current = 0;
    astPulseCounter.current = 0;
  }, [stepIndex]);

  const handleLeafReveal = useCallback(
    (line: number, col: number) => {
      const idx = stmtTokens.findIndex(
        (t) => t.line === line && t.col === col,
      );
      if (idx < 0) return;
      tokenPulseCounter.current += 1;
      const counter = tokenPulseCounter.current;
      setTokenPulses((prev) => ({ ...prev, [idx]: counter }));
    },
    [stmtTokens],
  );

  // Schedule AST-node pulses to fire when the Execution stage opens
  // (so the pulse animation is roughly synchronous with the env
  // binding appearing). Match new/changed bindings against
  // assigning-kind AST nodes (Assign, LetStmt, FuncDef, ClassDef)
  // whose `name` field equals the binding name.
  useEffect(() => {
    if (!stmtAst || !snapshot) return;
    const diff = bindingDiff(snapshot, previousSnapshot);
    if (diff.size === 0) return;
    const targets = findAssigningTargets(stmtAst, diff);
    if (targets.length === 0) return;
    const id = window.setTimeout(() => {
      const next: Record<string, AstPulse> = {};
      for (const tgt of targets) {
        astPulseCounter.current += 1;
        next[`${tgt.line}:${tgt.col}`] = {
          key: astPulseCounter.current,
          variant: tgt.variant,
        };
      }
      setAstPulses(next);
    }, STAGE_DELAYS.exec * 1000);
    return () => window.clearTimeout(id);
    // Re-run for each new snapshot. previousSnapshot is captured in
    // the diff; stmtAst is the matching subtree.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stepIndex, stmtAst]);

  return (
    <div className="space-y-3">
      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.source}
        icon={<Code2 className="h-3.5 w-3.5" />}
        title="1. Source"
        subtitle={`line ${stmtLine}:${stmtCol}`}
      >
        <SourceLine
          line={lineText}
          col={stmtCol}
          tokens={stmtTokens}
          lineNumber={stmtLine}
        />
      </StageBlock>

      <StageArrow stepIndex={stepIndex} delaySec={STAGE_DELAYS.tokens - 0.05} />

      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.tokens}
        icon={<ListTree className="h-3.5 w-3.5 rotate-90" />}
        title="2. Tokens"
        subtitle={`${stmtTokens.length} token${stmtTokens.length === 1 ? "" : "s"}`}
      >
        <TokensView
          tokens={stmtTokens}
          runKey={stepIndex}
          baseDelaySec={STAGE_DELAYS.tokens + 0.05}
          staggerSec={0.05}
          flyFrom="above"
          pulses={tokenPulses}
          empty="(no tokens on this line)"
        />
      </StageBlock>

      <StageArrow stepIndex={stepIndex} delaySec={STAGE_DELAYS.ast - 0.05} />

      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.ast}
        icon={<ListTree className="h-3.5 w-3.5" />}
        title="3. AST"
        subtitle={stmtAst?.__type__ ?? snapshot.statement_kind}
      >
        <AstView
          ast={stmtAst}
          baseDelaySec={STAGE_DELAYS.ast + 0.08}
          depthStaggerSec={0.08}
          empty="(no AST subtree available)"
          onLeafReveal={handleLeafReveal}
          nodePulses={astPulses}
        />
      </StageBlock>

      <StageArrow stepIndex={stepIndex} delaySec={STAGE_DELAYS.exec - 0.05} />

      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.exec}
        icon={<Terminal className="h-3.5 w-3.5" />}
        title="4. Execution"
        subtitle={snapshot.error ? "error" : "env updated"}
        accent={snapshot.error ? "error" : "exec"}
      >
        <ExecBlock
          snapshot={snapshot}
          previousSnapshot={previousSnapshot}
          stepIndex={stepIndex}
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
      initial={{ opacity: 0, y: 12, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        delay: delaySec,
        duration: 0.45,
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
          "mb-1.5 flex items-center justify-between gap-2 text-[10.5px] uppercase tracking-wider",
          accent === "error" ? "text-destructive/80" : "text-muted-foreground",
        )}
      >
        <span className="flex items-center gap-1.5">
          {icon}
          <span>{title}</span>
        </span>
        {subtitle && (
          <span className="font-mono normal-case text-foreground/60">
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
      animate={{ opacity: 0.6, y: 0 }}
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
}: {
  line: string;
  col: number;
  tokens: RotToken[];
  lineNumber: number;
}) {
  // Render the line text with per-token color spans so it visually
  // matches both the editor's syntax colors (v2.26.14) and the chip
  // palette (v2.26.12). When the Tokens stage opens below, chips fall
  // down from "above" — the user reads their colors as continuations
  // of the source-line spans.
  const segments = useMemo(
    () => splitLineByTokens(line, tokens, lineNumber),
    [line, tokens, lineNumber],
  );
  if (line.length === 0) {
    return (
      <pre className="rounded bg-zinc-900/60 px-2 py-1.5 font-mono text-[12.5px] text-muted-foreground">
        (empty line)
      </pre>
    );
  }
  return (
    <div className="space-y-0.5">
      <pre className="overflow-x-auto whitespace-pre rounded bg-zinc-900/60 px-2 py-1.5 font-mono text-[12.5px]">
        {segments.map((seg, i) =>
          seg.kind ? (
            <span key={i} className={tokenTextColor(seg.kind)}>
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
          className="overflow-x-auto whitespace-pre px-2 font-mono text-[10px] text-amber-400/80"
        >
          {" ".repeat(col - 1)}^
        </pre>
      )}
    </div>
  );
}

// Walk the tokens on a line in column order and split the line text
// into [pre-token whitespace, token text] segments. Token segments
// carry their `kind` so they can be colored; non-token segments get
// `kind=null` and render in a muted color.
function splitLineByTokens(
  line: string,
  tokens: RotToken[],
  lineNumber: number,
): { text: string; kind: string | null }[] {
  const onLine = tokens
    .filter((t) => t.line === lineNumber)
    .sort((a, b) => a.col - b.col);
  if (onLine.length === 0) {
    return [{ text: line, kind: null }];
  }
  const out: { text: string; kind: string | null }[] = [];
  let cursor = 0;
  for (const tok of onLine) {
    const start = Math.max(0, tok.col - 1);
    if (start > cursor) {
      out.push({ text: line.slice(cursor, start), kind: null });
    }
    const end = Math.min(line.length, start + tok.lexeme.length);
    if (end > start) {
      out.push({ text: line.slice(start, end), kind: tok.kind });
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
}: {
  snapshot: RotSnapshot;
  previousSnapshot: RotSnapshot | null;
  stepIndex: number;
}) {
  return (
    <div className="space-y-2">
      {snapshot.output_since_last && (
        <motion.div
          key={`${stepIndex}-out`}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            delay: STAGE_DELAYS.exec + 0.1,
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

// Renders the call stack as a sequence of pills: `global › funct
// greet › ...`. Pills are AnimatePresence children so entering a new
// scope slides a pill in from the right; leaving slides it back out.
// At top level there's exactly one pill ("global"), so it just sits
// quietly.
function CallBreadcrumb({ snapshot }: { snapshot: RotSnapshot }) {
  if (snapshot.env.length === 0) return null;
  // AnimatePresence requires motion components as DIRECT children —
  // wrapping pairs of (separator, pill) in a Fragment crashed because
  // Fragments don't accept the ref framer-motion attaches for exit
  // tracking. So flatMap to a flat list of motion.span siblings,
  // each with its own key.
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

// "iter 2/3" badge with a repeat icon. Renders next to the call
// breadcrumb when the current snapshot was taken inside a loop body.
// `total` is null for while loops (unknown ahead of time) — render
// "iter 2" without the slash in that case.
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
        Each click advances the interpreter one top-level statement.
      </p>
      <p>You&apos;ll see, for each statement:</p>
      <ol className="space-y-1 pl-4 [list-style:decimal]">
        <li>
          <span className="text-foreground/80">Source</span> — the line that
          just ran.
        </li>
        <li>
          <span className="text-foreground/80">Tokens</span> — the lexer&apos;s
          output for that line.
        </li>
        <li>
          <span className="text-foreground/80">AST</span> — the parsed subtree.
        </li>
        <li>
          <span className="text-foreground/80">Execution</span> — what the
          interpreter did with it.
        </li>
      </ol>
    </div>
  );
}

// ─── Statement-scoped data extraction ────────────────────────────────

function tokensForStatement(
  tokens: RotToken[],
  ast: AstNode | null,
  stmtLine: number,
  stmtCol: number,
  stmtKind: string,
): RotToken[] {
  // First try: use the snapshot's AST subtree's line range to find the
  // right tokens. Falls back to "all tokens on stmt_line" if the AST
  // lookup fails (defensive).
  const subtree = findStatementAst(ast, stmtLine, stmtCol, stmtKind);
  if (!subtree) {
    return tokens.filter((t) => t.line === stmtLine);
  }
  const range = lineRange(subtree);
  if (!range) {
    return tokens.filter((t) => t.line === stmtLine);
  }
  return tokens.filter((t) => t.line >= range.min && t.line <= range.max);
}

// Walk the AST looking for a node with matching (line, col, __type__).
// Used instead of `body[stepIndex]` because deep stepping yields
// snapshots for nested statements that aren't direct children of
// program.body.
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

// Returns a Map of binding-name → "new" | "changed" based on the env
// diff between two snapshots. Matches frames by (scope_kind,
// scope_label) — so a binding promoted from "new" in one snapshot
// to "still present" in the next won't keep firing as new.
function bindingDiff(
  snap: RotSnapshot,
  prev: RotSnapshot | null,
): Map<string, "new" | "changed"> {
  const out = new Map<string, "new" | "changed">();
  for (const frame of snap.env) {
    const prevFrame = prev
      ? prev.env.find(
          (f) =>
            f.scope_kind === frame.scope_kind &&
            f.scope_label === frame.scope_label,
        ) ?? null
      : null;
    for (const [name, value] of Object.entries(frame.bindings)) {
      if (!prevFrame || !(name in prevFrame.bindings)) {
        out.set(name, "new");
      } else if (prevFrame.bindings[name] !== value) {
        out.set(name, "changed");
      }
    }
  }
  return out;
}

// Walk the statement AST looking for nodes that assign a binding —
// `Assign`, `LetStmt`, `FuncDef`, `ClassDef`, `IndexAssign`,
// `MemberAssign`. For each such node whose `name` is in `diff`,
// record its position + the pulse variant (new vs changed). The
// Step panel uses this to highlight the *cause* of an env change.
function findAssigningTargets(
  ast: AstNode,
  diff: Map<string, "new" | "changed">,
): Array<{ line: number; col: number; variant: "new" | "changed" }> {
  const ASSIGNING_KINDS = new Set([
    "Assign",
    "LetStmt",
    "FuncDef",
    "ClassDef",
  ]);
  const out: Array<{
    line: number;
    col: number;
    variant: "new" | "changed";
  }> = [];
  function visit(v: AstValue): void {
    if (v === null || v === undefined) return;
    if (typeof v !== "object") return;
    if (Array.isArray(v)) {
      for (const x of v) visit(x);
      return;
    }
    const n = v as AstNode;
    if (ASSIGNING_KINDS.has(n.__type__)) {
      const name = typeof n.name === "string" ? n.name : null;
      const variant = name ? diff.get(name) : undefined;
      if (name && variant) {
        const line = typeof n.line === "number" ? n.line : 0;
        const col = typeof n.col === "number" ? n.col : 0;
        if (line > 0 && col > 0) {
          out.push({ line, col, variant });
        }
      }
    }
    for (const [k, child] of Object.entries(n)) {
      if (k === "__type__" || k === "line" || k === "col") continue;
      visit(child as AstValue);
    }
  }
  visit(ast);
  return out;
}

function lineRange(node: AstValue): { min: number; max: number } | null {
  // Walk the subtree collecting `line` fields. Returns null if nothing
  // useful found.
  let min = Number.POSITIVE_INFINITY;
  let max = 0;

  function visit(v: AstValue) {
    if (v === null || v === undefined) return;
    if (typeof v !== "object") return;
    if (Array.isArray(v)) {
      for (const x of v) visit(x);
      return;
    }
    const line = (v as { line?: AstValue }).line;
    if (typeof line === "number" && line > 0) {
      if (line < min) min = line;
      if (line > max) max = line;
    }
    for (const [k, child] of Object.entries(v)) {
      if (k === "__type__" || k === "line" || k === "col") continue;
      visit(child as AstValue);
    }
  }
  visit(node);
  if (max === 0) return null;
  return { min, max };
}
