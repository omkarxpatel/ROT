"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

import type { AstNode, AstValue } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

// One-shot pulse signal for an AST node, keyed by `${line}:${col}`.
// `variant` controls the color so the pulse matches the env dot:
// emerald for a new binding, amber for a changed value.
export interface AstPulse {
  key: number;
  variant: "new" | "changed";
}

interface AstViewProps {
  ast: AstNode | null;
  // Per-Step / per-Run delay for the root entrance.
  baseDelaySec?: number;
  // Multiplier on depth for the per-node stagger.
  depthStaggerSec?: number;
  empty?: string;
  // Optional callback fired after a node with a "primary" field
  // (NumberLit, StringLit, Identifier, BinaryOp, ...) finishes its
  // entrance animation. The Step panel uses this to pulse the
  // matching token chip so the user reads parse as a real lex→AST
  // connection.
  onLeafReveal?: (line: number, col: number) => void;
  // Pulses keyed by node position. When an entry's `key` increments,
  // the matching node fires a one-shot ring overlay. Used by the
  // Step panel to highlight the AST node responsible for a newly-
  // bound or changed env entry — closes the parse → execute chain.
  nodePulses?: Record<string, AstPulse>;
}

export function AstView({
  ast,
  baseDelaySec = 0,
  depthStaggerSec = 0.08,
  empty,
  onLeafReveal,
  nodePulses,
}: AstViewProps) {
  if (!ast) {
    return (
      <div className="text-xs text-muted-foreground">
        {empty ?? "No AST yet."}
      </div>
    );
  }
  return (
    <div className="font-mono text-[12.5px]">
      <AstNodeView
        node={ast}
        depth={0}
        baseDelaySec={baseDelaySec}
        depthStaggerSec={depthStaggerSec}
        onLeafReveal={onLeafReveal}
        nodePulses={nodePulses}
      />
    </div>
  );
}

interface AstNodeProps {
  node: AstNode;
  depth: number;
  baseDelaySec: number;
  depthStaggerSec: number;
  onLeafReveal?: (line: number, col: number) => void;
  nodePulses?: Record<string, AstPulse>;
}

function AstNodeView({
  node,
  depth,
  baseDelaySec,
  depthStaggerSec,
  onLeafReveal,
  nodePulses,
}: AstNodeProps) {
  const [open, setOpen] = useState(true);
  const type = node.__type__;
  const label = humanLabel(type);
  const primary = primaryField(type, node);

  // Partition the node's fields:
  // - hidden: line, col, the primary field (already rendered in label)
  // - inline: remaining primitives (rare — most useful ones are primary)
  // - nested: AST nodes and arrays
  const entries = useMemo(() => {
    const all = Object.entries(node).filter(([k]) => k !== "__type__");
    const inline: [string, string | number | boolean | null | undefined][] = [];
    const nested: [string, AstValue][] = [];
    const primaryKey = primary?.key ?? null;
    for (const [k, v] of all) {
      if (k === "line" || k === "col") continue;
      if (k === primaryKey) continue;
      if (isPrimitive(v)) {
        inline.push([k, v]);
      } else {
        // Skip empty arrays — they're noise for things like a FuncDef
        // with no parameters or a Block with no statements.
        if (Array.isArray(v) && v.length === 0) continue;
        nested.push([k, v]);
      }
    }
    return { inline, nested };
  }, [node, primary?.key]);

  const indent = `${depth * 12}px`;
  const delay = baseDelaySec + depth * depthStaggerSec;

  // After this node's entrance animation completes, if it has a
  // primary field (i.e. it's a leaf-ish node with one inline value),
  // signal to the Step panel to pulse the matching source token. We
  // only fire for primary-field nodes — Block / IfStmt / etc. have no
  // "key thing" to point back at, so they'd just create noise.
  const handleAnimationComplete = () => {
    if (!onLeafReveal || !primary) return;
    const line = typeof node.line === "number" ? node.line : 0;
    const col = typeof node.col === "number" ? node.col : 0;
    if (line > 0 && col > 0) onLeafReveal(line, col);
  };

  // Look up a pulse signal for this node by `${line}:${col}`. When
  // `pulse.key` changes (new pulse counter), the overlay re-keys and
  // fires its one-shot ring animation.
  const nodeLine = typeof node.line === "number" ? node.line : 0;
  const nodeCol = typeof node.col === "number" ? node.col : 0;
  const pulse = nodePulses?.[`${nodeLine}:${nodeCol}`];

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
      onAnimationComplete={handleAnimationComplete}
      style={{ paddingLeft: indent }}
    >
      <div className="relative inline-block w-full">
        <button
          onClick={() => setOpen((o) => !o)}
          className="group flex w-full items-center gap-1.5 text-left hover:text-foreground"
          title={type}
        >
          <ChevronRight
            className={cn(
              "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform",
              open && "rotate-90",
            )}
          />
          <span className="font-semibold text-purple-300">{label}</span>
          {primary && (
            <span className={cn("font-mono", primary.colorClass)}>
              {primary.display}
            </span>
          )}
          {entries.inline.length > 0 && (
            <span className="text-muted-foreground">
              {entries.inline.map(([k, v], i) => (
                <span key={k}>
                  {i === 0 ? " " : "  "}
                  <span className="text-sky-400">{k}</span>
                  <span className="text-zinc-500">=</span>
                  <span className="text-emerald-400">{formatPrimitive(v)}</span>
                </span>
              ))}
            </span>
          )}
        </button>
        {pulse && (
          <motion.span
            key={`pulse-${pulse.key}`}
            initial={{ opacity: 0.85, scale: 0.96 }}
            animate={{ opacity: 0, scale: 1.5 }}
            transition={{ duration: 0.7, ease: "easeOut" }}
            className={cn(
              "pointer-events-none absolute inset-0 rounded ring-2",
              pulse.variant === "new"
                ? "ring-emerald-400"
                : "ring-amber-400",
            )}
            aria-hidden
          />
        )}
      </div>
      {open && entries.nested.length > 0 && (
        <div className="mt-0.5 space-y-0.5 border-l border-border/40 pl-2 ml-1.5">
          {entries.nested.map(([k, v]) => (
            <div key={k}>
              <div
                className="text-[11px] text-muted-foreground"
                style={{ paddingLeft: `${(depth + 1) * 12}px` }}
              >
                {humanField(k)}:
              </div>
              <AstValueView
                value={v}
                depth={depth + 1}
                baseDelaySec={baseDelaySec}
                depthStaggerSec={depthStaggerSec}
                onLeafReveal={onLeafReveal}
                nodePulses={nodePulses}
              />
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

function AstValueView({
  value,
  depth,
  baseDelaySec,
  depthStaggerSec,
  onLeafReveal,
  nodePulses,
}: {
  value: AstValue;
  depth: number;
  baseDelaySec: number;
  depthStaggerSec: number;
  onLeafReveal?: (line: number, col: number) => void;
  nodePulses?: Record<string, AstPulse>;
}) {
  if (value === null || value === undefined) {
    return (
      <div
        className="text-[11.5px] text-zinc-500"
        style={{ paddingLeft: `${depth * 12}px` }}
      >
        null
      </div>
    );
  }
  if (Array.isArray(value)) {
    if (value.length === 0) {
      // Empty arrays are filtered upstream, but defend anyway.
      return null;
    }
    return (
      <div>
        {value.map((v, i) => (
          <AstValueView
            key={i}
            value={v}
            depth={depth}
            baseDelaySec={baseDelaySec}
            depthStaggerSec={depthStaggerSec}
            onLeafReveal={onLeafReveal}
            nodePulses={nodePulses}
          />
        ))}
      </div>
    );
  }
  if (isPrimitive(value)) {
    return (
      <div
        className="text-[11.5px] text-emerald-400"
        style={{ paddingLeft: `${depth * 12}px` }}
      >
        {formatPrimitive(value)}
      </div>
    );
  }
  return (
    <AstNodeView
      node={value as AstNode}
      depth={depth}
      baseDelaySec={baseDelaySec}
      depthStaggerSec={depthStaggerSec}
      onLeafReveal={onLeafReveal}
      nodePulses={nodePulses}
    />
  );
}

// ─── Humanization ───────────────────────────────────────────────────

// Plain-English label for each AST node kind. The technical name still
// lives in the hover tooltip so a curious reader can see it.
const NODE_LABEL: Record<string, string> = {
  Program: "Program",
  Block: "Block",
  ExprStmt: "Expression",
  Assign: "Assign",
  LetStmt: "Let",
  FuncDef: "Function",
  ClassDef: "Class",
  Return: "Return",
  IfStmt: "If",
  ElifBranch: "Elif",
  WhileStmt: "While",
  ForStmt: "For",
  TryCatch: "Try / catch",
  ThrowStmt: "Throw",
  BreakStmt: "Break",
  ContinueStmt: "Continue",
  ImportStmt: "Import",
  IndexAssign: "Index assign",
  MemberAssign: "Field assign",
  Call: "Call",
  BinaryOp: "Binary",
  UnaryOp: "Unary",
  Index: "Index",
  Slice: "Slice",
  MemberAccess: "Field",
  ListLit: "List",
  DictLit: "Dict",
  NumberLit: "Number",
  StringLit: "String",
  BoolLit: "Boolean",
  NullLit: "null",
  Identifier: "Name",
};

function humanLabel(type: string): string {
  return NODE_LABEL[type] ?? type;
}

// The "primary" field is the one that's most useful displayed inline
// alongside the node label. For a `NumberLit` it's `value`; for a
// `BinaryOp` it's `op` (so we read "Binary +" instead of "BinaryOp
// op='+'"). Most nodes have no primary field — they're rendered as
// just the label with children below.
function primaryField(
  type: string,
  node: AstNode,
):
  | {
      key: string;
      display: string;
      colorClass: string;
    }
  | null {
  const key = PRIMARY_KEY[type];
  if (!key) return null;
  const raw = node[key];
  if (!isPrimitive(raw)) return null;
  const display = renderPrimary(type, raw);
  const colorClass = PRIMARY_COLOR[type] ?? "text-emerald-300";
  return { key, display, colorClass };
}

const PRIMARY_KEY: Record<string, string> = {
  NumberLit: "value",
  StringLit: "value",
  BoolLit: "value",
  Identifier: "name",
  BinaryOp: "op",
  UnaryOp: "op",
  Assign: "name",
  LetStmt: "name",
  FuncDef: "name",
  ClassDef: "name",
  MemberAccess: "member",
  MemberAssign: "member",
  ImportStmt: "path",
};

const PRIMARY_COLOR: Record<string, string> = {
  NumberLit: "text-cyan-300",
  StringLit: "text-amber-300",
  BoolLit: "text-emerald-300",
  Identifier: "text-sky-300",
  BinaryOp: "text-rose-300",
  UnaryOp: "text-rose-300",
  Assign: "text-sky-300",
  LetStmt: "text-sky-300",
  FuncDef: "text-sky-300",
  ClassDef: "text-sky-300",
  MemberAccess: "text-sky-300",
  MemberAssign: "text-sky-300",
  ImportStmt: "text-amber-300",
};

function renderPrimary(
  type: string,
  raw: string | number | boolean | null | undefined,
): string {
  if (raw === null || raw === undefined) return "null";
  if (type === "StringLit" || type === "ImportStmt") {
    return JSON.stringify(String(raw));
  }
  return String(raw);
}

const FIELD_LABEL: Record<string, string> = {
  body: "body",
  callee: "callee",
  args: "args",
  left: "left",
  right: "right",
  operand: "operand",
  target: "target",
  index: "index",
  start: "start",
  stop: "stop",
  step: "step",
  cond: "if",
  then_block: "then",
  else_block: "else",
  elifs: "elifs",
  catch_block: "catch",
  finally_block: "finally",
  try_block: "try",
  params: "params",
  value: "value",
  values: "values",
  pairs: "pairs",
  bases: "bases",
  members: "members",
  expr: "expr",
};

function humanField(key: string): string {
  return FIELD_LABEL[key] ?? key;
}

function isPrimitive(
  v: unknown,
): v is string | number | boolean | null | undefined {
  return (
    v === null ||
    v === undefined ||
    typeof v === "string" ||
    typeof v === "number" ||
    typeof v === "boolean"
  );
}

function formatPrimitive(
  v: string | number | boolean | null | undefined,
): string {
  if (v === null || v === undefined) return "null";
  if (typeof v === "string") return JSON.stringify(v);
  return String(v);
}
