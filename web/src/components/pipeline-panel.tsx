"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { ScrollArea } from "@/components/ui/scroll-area";
import { EnvView } from "@/components/env-view";
import type {
  AstNode,
  AstValue,
  RotSnapshot,
  RotToken,
} from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface PipelinePanelProps {
  tokens: RotToken[];
  ast: AstNode | null;
  trace: string;
  // Bumped on every run so the token stagger animation re-fires.
  runKey: number;
  // When non-null (Animate mode), an extra "Env" accordion item is
  // rendered at the top, expanded by default, showing the current
  // snapshot's scope chain. Otherwise hidden.
  currentSnapshot?: RotSnapshot | null;
  // Previous snapshot (one step back). Used by EnvView for "new" /
  // "changed" binding indicators and the explainer copy.
  previousSnapshot?: RotSnapshot | null;
  // Bumped per step so EnvView can animate the per-frame fade-in.
  stepKey?: number;
}

export function PipelinePanel({
  tokens,
  ast,
  trace,
  runKey,
  currentSnapshot,
  previousSnapshot,
  stepKey,
}: PipelinePanelProps) {
  // When in Animate mode, default-expand Env (alongside the other
  // sections). When not, the Env item isn't rendered at all.
  const defaultOpen = currentSnapshot
    ? ["env", "tokens", "ast", "trace"]
    : ["tokens", "ast", "trace"];
  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-border/60 px-3 py-2 text-xs uppercase tracking-wider text-muted-foreground">
        Pipeline
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <Accordion type="multiple" defaultValue={defaultOpen} className="w-full">
          {currentSnapshot && (
            <AccordionItem value="env" className="border-b border-border/60">
              <AccordionTrigger>
                <span>
                  Env
                  <span className="ml-2 text-xs text-muted-foreground">
                    ({currentSnapshot.env.reduce(
                      (n, f) => n + Object.keys(f.bindings).length,
                      0,
                    )}{" "}
                    bindings)
                  </span>
                </span>
              </AccordionTrigger>
              <AccordionContent>
                <EnvView
                  snapshot={currentSnapshot}
                  previousSnapshot={previousSnapshot ?? null}
                  stepKey={stepKey ?? 0}
                />
              </AccordionContent>
            </AccordionItem>
          )}
          <AccordionItem value="tokens" className="border-b border-border/60">
            <AccordionTrigger>
              <span>Tokens {tokens.length > 0 && <span className="ml-2 text-xs text-muted-foreground">({tokens.length})</span>}</span>
            </AccordionTrigger>
            <AccordionContent>
              <TokensView tokens={tokens} runKey={runKey} />
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="ast" className="border-b border-border/60">
            <AccordionTrigger>
              <span>AST</span>
            </AccordionTrigger>
            <AccordionContent>
              <AstView ast={ast} />
            </AccordionContent>
          </AccordionItem>
          <AccordionItem value="trace" className="border-b-0">
            <AccordionTrigger>
              <span>Trace</span>
            </AccordionTrigger>
            <AccordionContent>
              <TraceView trace={trace} />
            </AccordionContent>
          </AccordionItem>
        </Accordion>
      </ScrollArea>
    </div>
  );
}

// ─── Tokens ──────────────────────────────────────────────────────────

function tokenClass(kind: string): string {
  // Map ROT token kinds → tailwind palette classes (defined in globals.css).
  if (kind === "STRING_LIT" || kind === "F_STRING_LIT") return "chip-string";
  if (kind === "NUMBER_LIT") return "chip-number";
  if (kind === "TRUE" || kind === "FALSE" || kind === "NULL") return "chip-literal";
  if (kind === "IDENT") return "chip-identifier";
  if (
    kind === "L_PAREN" ||
    kind === "R_PAREN" ||
    kind === "L_CURLY" ||
    kind === "R_CURLY" ||
    kind === "L_BRACKET" ||
    kind === "R_BRACKET" ||
    kind === "COMMA" ||
    kind === "PIPE" ||
    kind === "DOT" ||
    kind === "COLON" ||
    kind === "SEMICOLON"
  ) {
    return "chip-punct";
  }
  // Operators / equality / comparison / arithmetic.
  if (
    kind === "PLUS" ||
    kind === "MINUS" ||
    kind === "STAR" ||
    kind === "SLASH" ||
    kind === "PERCENT" ||
    kind === "EQ_EQ" ||
    kind === "NEQ" ||
    kind === "LE" ||
    kind === "GE" ||
    kind === "LESSTHAN" ||
    kind === "GREATERTHAN" ||
    kind === "SETVALUE" ||
    kind === "PLUS_EQ" ||
    kind === "MINUS_EQ" ||
    kind === "STAR_EQ" ||
    kind === "SLASH_EQ" ||
    kind === "PERCENT_EQ"
  ) {
    return "chip-operator";
  }
  // Default: keywords (any other named kind).
  return "chip-keyword";
}

function TokensView({ tokens, runKey }: { tokens: RotToken[]; runKey: number }) {
  if (tokens.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        No tokens yet. Run the program to populate.
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {tokens.map((t, i) => (
        <motion.div
          // Including runKey in the key forces re-mount per run so the
          // stagger animation re-fires.
          key={`${runKey}-${i}`}
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: Math.min(i, 80) * 0.012, duration: 0.16 }}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-2 py-1 font-mono text-[11px]",
            tokenClass(t.kind),
          )}
          title={`${t.kind} at line ${t.line}:${t.col}`}
        >
          <span className="font-semibold">{escapeLexeme(t.lexeme)}</span>
          <span className="text-[10px] opacity-70">{t.kind}</span>
          <span className="text-[10px] opacity-50">
            {t.line}:{t.col}
          </span>
        </motion.div>
      ))}
    </div>
  );
}

function escapeLexeme(s: string): string {
  if (s === "\n") return "\\n";
  if (s === "\t") return "\\t";
  if (s === " ") return "·";
  return s;
}

// ─── AST ─────────────────────────────────────────────────────────────

function AstView({ ast }: { ast: AstNode | null }) {
  if (!ast) {
    return (
      <div className="text-xs text-muted-foreground">
        No AST yet. Run a program that parses cleanly.
      </div>
    );
  }
  return (
    <div className="font-mono text-[12.5px]">
      <AstNodeView node={ast} depth={0} />
    </div>
  );
}

interface AstNodeProps {
  node: AstNode;
  depth: number;
}

function AstNodeView({ node, depth }: AstNodeProps) {
  // Collapse-by-default for the root only; nested nodes start expanded
  // so the tree feels alive on first render.
  const [open, setOpen] = useState(true);

  // Partition the node fields into (children with __type__ or arrays of
  // such) vs (primitive scalars), so we can render scalars inline.
  const entries = useMemo(() => {
    const all = Object.entries(node).filter(([k]) => k !== "__type__");
    const inline: [string, string | number | boolean | null | undefined][] =
      [];
    const nested: [string, AstValue][] = [];
    for (const [k, v] of all) {
      if (isPrimitive(v)) {
        inline.push([k, v]);
      } else {
        nested.push([k, v]);
      }
    }
    return { inline, nested };
  }, [node]);

  const indent = `${depth * 12}px`;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.18 }}
      style={{ paddingLeft: indent }}
    >
      <button
        onClick={() => setOpen((o) => !o)}
        className="group flex w-full items-center gap-1.5 text-left hover:text-foreground"
      >
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 shrink-0 text-muted-foreground transition-transform",
            open && "rotate-90",
          )}
        />
        <span className="font-semibold text-purple-300">{node.__type__}</span>
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
      {open && entries.nested.length > 0 && (
        <div className="mt-0.5 space-y-0.5 border-l border-border/40 pl-2 ml-1.5">
          {entries.nested.map(([k, v]) => (
            <div key={k}>
              <div
                className="text-[11px] text-muted-foreground"
                style={{ paddingLeft: `${(depth + 1) * 12}px` }}
              >
                {k}:
              </div>
              <AstValueView value={v} depth={depth + 1} />
            </div>
          ))}
        </div>
      )}
    </motion.div>
  );
}

function AstValueView({ value, depth }: { value: AstValue; depth: number }) {
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
      return (
        <div
          className="text-[11.5px] text-zinc-500"
          style={{ paddingLeft: `${depth * 12}px` }}
        >
          []
        </div>
      );
    }
    return (
      <div>
        {value.map((v, i) => (
          <AstValueView key={i} value={v} depth={depth} />
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
  // AstNode
  return <AstNodeView node={value as AstNode} depth={depth} />;
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

// ─── Trace ───────────────────────────────────────────────────────────

function TraceView({ trace }: { trace: string }) {
  if (!trace) {
    return (
      <div className="text-xs text-muted-foreground">
        No trace yet. Run the program first.
      </div>
    );
  }
  return (
    <pre className="whitespace-pre-wrap font-mono text-[12px] text-foreground/80">
      {trace}
    </pre>
  );
}
