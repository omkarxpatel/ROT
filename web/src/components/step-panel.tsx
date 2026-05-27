"use client";

import { Fragment, useMemo } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ArrowDown,
  ChevronRight,
  Code2,
  ListTree,
  Sparkles,
  Terminal,
} from "lucide-react";

import { AstView } from "@/components/ast-view";
import { EnvView } from "@/components/env-view";
import { ScrollArea } from "@/components/ui/scroll-area";
import { TokensView } from "@/components/tokens-view";
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

  // 2) The tokens on that line (and any tokens whose line falls between
  // this statement's start line and the next statement's start line,
  // catching multi-line statements like funct definitions).
  const stmtTokens = useMemo(() => {
    return tokensForStatement(tokens, ast, stepIndex, stmtLine);
  }, [tokens, ast, stepIndex, stmtLine]);

  // 3) The AST subtree for this top-level statement. The program's
  // body[stepIndex] is the statement node corresponding to this
  // snapshot.
  const stmtAst = useMemo<AstNode | null>(() => {
    return statementAst(ast, stepIndex);
  }, [ast, stepIndex]);

  return (
    <div className="space-y-3">
      <StageBlock
        stepIndex={stepIndex}
        delaySec={STAGE_DELAYS.source}
        icon={<Code2 className="h-3.5 w-3.5" />}
        title="1. Source"
        subtitle={`line ${stmtLine}:${stmtCol}`}
      >
        <SourceLine line={lineText} col={stmtCol} />
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

function SourceLine({ line, col }: { line: string; col: number }) {
  // Show the line text in code-monospace. Caret pointing at the
  // statement column for orientation.
  const trimmed = line.length === 0 ? "(empty line)" : line;
  return (
    <div className="space-y-0.5">
      <pre className="overflow-x-auto whitespace-pre rounded bg-zinc-900/60 px-2 py-1.5 font-mono text-[12.5px] text-foreground/90">
        {trimmed}
      </pre>
      {line.length > 0 && col >= 1 && col <= line.length + 1 && (
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
  return (
    <div className="flex items-center gap-1 overflow-hidden">
      <AnimatePresence mode="popLayout" initial={false}>
        {snapshot.env.map((frame, i) => (
          <Fragment key={`${frame.scope_label}-${i}`}>
            {i > 0 && (
              <motion.span
                key={`sep-${frame.scope_label}-${i}`}
                initial={{ opacity: 0, x: -4 }}
                animate={{ opacity: 0.5, x: 0 }}
                exit={{ opacity: 0, x: -4 }}
                transition={{ duration: 0.25 }}
                className="text-muted-foreground"
                aria-hidden
              >
                <ChevronRight className="h-3 w-3" />
              </motion.span>
            )}
            <motion.span
              layout
              initial={{ opacity: 0, x: 12, scale: 0.94 }}
              animate={{ opacity: 1, x: 0, scale: 1 }}
              exit={{ opacity: 0, x: 12, scale: 0.94 }}
              transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
              className={cn(
                "rounded-full border px-2 py-0.5 font-mono text-[10.5px]",
                i === snapshot.env.length - 1
                  ? "border-amber-500/40 bg-amber-500/10 text-amber-300"
                  : "border-border/60 bg-background/40 text-muted-foreground",
              )}
            >
              {frame.scope_label}
            </motion.span>
          </Fragment>
        ))}
      </AnimatePresence>
    </div>
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
  stepIndex: number,
  stmtLine: number,
): RotToken[] {
  // First try: use the AST subtree's line range to find the right
  // tokens. Falls back to "all tokens on stmt_line" if the AST isn't
  // available.
  const subtree = statementAst(ast, stepIndex);
  if (!subtree) {
    return tokens.filter((t) => t.line === stmtLine);
  }
  const range = lineRange(subtree);
  if (!range) {
    return tokens.filter((t) => t.line === stmtLine);
  }
  return tokens.filter((t) => t.line >= range.min && t.line <= range.max);
}

function statementAst(ast: AstNode | null, stepIndex: number): AstNode | null {
  if (!ast) return null;
  const body = (ast as { body?: AstValue }).body;
  if (!Array.isArray(body)) return null;
  const stmt = body[stepIndex];
  if (!stmt || typeof stmt !== "object" || Array.isArray(stmt)) return null;
  return stmt as AstNode;
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
