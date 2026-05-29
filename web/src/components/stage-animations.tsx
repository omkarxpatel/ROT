"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";

import { cn } from "@/lib/utils";

// Three small, self-contained, looping animations — one per pipeline
// stage. Each one runs on a setInterval timer keyed off a single phase
// counter, so the framer-motion `key` + `AnimatePresence` patterns can
// drive the transitions declaratively. No Pyodide, no runtime — pure
// declarative motion over hand-curated data.

// ===================================================================
// Shared frame chrome
// ===================================================================

interface StageFrameProps {
  label: string;
  caption: string;
  children: React.ReactNode;
  accent: "violet" | "cyan" | "amber";
}

const ACCENT_BORDER: Record<StageFrameProps["accent"], string> = {
  violet: "border-violet-500/30 shadow-[0_0_0_1px_rgba(139,92,246,0.05)]",
  cyan: "border-cyan-500/30 shadow-[0_0_0_1px_rgba(6,182,212,0.05)]",
  amber: "border-amber-500/30 shadow-[0_0_0_1px_rgba(245,158,11,0.05)]",
};

const ACCENT_LABEL: Record<StageFrameProps["accent"], string> = {
  violet: "text-violet-300",
  cyan: "text-cyan-300",
  amber: "text-amber-300",
};

function StageFrame({ label, caption, children, accent }: StageFrameProps) {
  return (
    <div
      className={cn(
        "flex h-full flex-col overflow-hidden rounded-lg border bg-card/50",
        ACCENT_BORDER[accent],
      )}
    >
      <div className="flex items-baseline justify-between border-b border-border/40 px-3 py-2">
        <span
          className={cn(
            "font-mono text-xs uppercase tracking-wider",
            ACCENT_LABEL[accent],
          )}
        >
          {label}
        </span>
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          live
        </span>
      </div>
      <div className="flex flex-1 flex-col gap-3 p-4">{children}</div>
      <div className="border-t border-border/40 bg-background/40 px-3 py-2 text-[11px] leading-snug text-muted-foreground">
        {caption}
      </div>
    </div>
  );
}

// usePhase: cycles a counter 0..N-1 with a configurable per-phase delay.
// The first phase fires immediately on mount so animations start
// visible (no awkward empty frame at the start).
function usePhase(phaseCount: number, delayMs = 1200) {
  const [phase, setPhase] = useState(0);
  useEffect(() => {
    const id = window.setInterval(() => {
      setPhase((p) => (p + 1) % phaseCount);
    }, delayMs);
    return () => window.clearInterval(id);
  }, [phaseCount, delayMs]);
  return phase;
}

// ===================================================================
// Lexer animation — characters group into tokens.
// ===================================================================

interface CharBucket {
  text: string;
  kind: "ident" | "op" | "lit" | "punct";
}

// Each phase highlights a contiguous slice of the source as the lexer
// "consumes" it; the corresponding token chip then appears below.
interface LexerPhase {
  highlight: [number, number];
  emitted: CharBucket[];
}

const LEXER_SOURCE = 'coutln("hi")';
// Slices map to: `coutln` (ident), `(` (punct), `"hi"` (lit), `)` (punct).
const LEXER_PHASES: LexerPhase[] = [
  { highlight: [0, 0], emitted: [] },
  {
    highlight: [0, 6],
    emitted: [{ text: "coutln", kind: "ident" }],
  },
  {
    highlight: [6, 7],
    emitted: [
      { text: "coutln", kind: "ident" },
      { text: "(", kind: "punct" },
    ],
  },
  {
    highlight: [7, 11],
    emitted: [
      { text: "coutln", kind: "ident" },
      { text: "(", kind: "punct" },
      { text: '"hi"', kind: "lit" },
    ],
  },
  {
    highlight: [11, 12],
    emitted: [
      { text: "coutln", kind: "ident" },
      { text: "(", kind: "punct" },
      { text: '"hi"', kind: "lit" },
      { text: ")", kind: "punct" },
    ],
  },
];

const TOKEN_KIND_COLOR: Record<CharBucket["kind"], string> = {
  ident: "text-sky-300 border-sky-500/30 bg-sky-500/10",
  op: "text-amber-200 border-amber-500/30 bg-amber-500/10",
  lit: "text-emerald-200 border-emerald-500/30 bg-emerald-500/10",
  punct: "text-muted-foreground border-border/60 bg-muted/30",
};

export function LexerAnimation() {
  const phase = usePhase(LEXER_PHASES.length, 1100);
  const { highlight, emitted } = LEXER_PHASES[phase];
  return (
    <StageFrame
      label="Lexer"
      caption="A char-by-char tokenizer. Groups characters into typed tokens that carry line + column."
      accent="violet"
    >
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground/70">
        <span>characters</span>
      </div>
      <div className="rounded-md border border-border/40 bg-background/60 px-3 py-2 font-mono text-[13px]">
        {Array.from(LEXER_SOURCE).map((ch, i) => {
          const isActive = i >= highlight[0] && i < highlight[1];
          return (
            <motion.span
              key={i}
              animate={{
                color: isActive ? "#fcd34d" : "rgba(255,255,255,0.55)",
                backgroundColor: isActive
                  ? "rgba(245,158,11,0.15)"
                  : "rgba(0,0,0,0)",
              }}
              transition={{ duration: 0.2 }}
              className="rounded-sm px-[1px]"
            >
              {ch === " " ? " " : ch}
            </motion.span>
          );
        })}
      </div>
      <div className="flex items-center text-[10px] uppercase tracking-wider text-muted-foreground/70">
        tokens
      </div>
      <div className="flex min-h-[2rem] flex-wrap items-center gap-1.5">
        <AnimatePresence mode="popLayout">
          {emitted.map((t, i) => (
            <motion.span
              key={`${phase}-${i}`}
              initial={{ opacity: 0, y: -6, scale: 0.85 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.22, ease: "easeOut" }}
              className={cn(
                "rounded border px-1.5 py-0.5 font-mono text-[11px]",
                TOKEN_KIND_COLOR[t.kind],
              )}
            >
              {t.text}
            </motion.span>
          ))}
        </AnimatePresence>
      </div>
    </StageFrame>
  );
}

// ===================================================================
// Parser animation — tokens fold into an AST tree.
// ===================================================================

// Three phases for a tiny `1 + 2 * 3` expression:
//   1. just the flat token list (1 + 2 * 3)
//   2. the * binds first (2 * 3 → Mul)
//   3. the + wraps the whole thing
const PARSER_PHASES: { tokens: string[]; tree: TreeNode | null }[] = [
  { tokens: ["1", "+", "2", "*", "3"], tree: null },
  {
    tokens: ["1", "+", "2", "*", "3"],
    tree: { label: "BinaryOp(*)", children: [{ label: "2" }, { label: "3" }] },
  },
  {
    tokens: ["1", "+", "2", "*", "3"],
    tree: {
      label: "BinaryOp(+)",
      children: [
        { label: "1" },
        {
          label: "BinaryOp(*)",
          children: [{ label: "2" }, { label: "3" }],
        },
      ],
    },
  },
];

interface TreeNode {
  label: string;
  children?: TreeNode[];
}

export function ParserAnimation() {
  const phase = usePhase(PARSER_PHASES.length, 1500);
  const { tokens, tree } = PARSER_PHASES[phase];
  return (
    <StageFrame
      label="Parser"
      caption="Recursive descent for statements, Pratt for expressions. Operator precedence falls out naturally."
      accent="cyan"
    >
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
        tokens
      </div>
      <div className="flex flex-wrap items-center gap-1.5">
        {tokens.map((t, i) => (
          <span
            key={i}
            className={cn(
              "rounded border px-1.5 py-0.5 font-mono text-[11px]",
              /^\d+$/.test(t)
                ? "text-emerald-200 border-emerald-500/30 bg-emerald-500/10"
                : "text-amber-200 border-amber-500/30 bg-amber-500/10",
            )}
          >
            {t}
          </span>
        ))}
      </div>
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground/70">
        ast
      </div>
      <div className="flex min-h-[5rem] flex-1 items-start">
        <AnimatePresence mode="wait">
          <motion.div
            key={phase}
            initial={{ opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="font-mono text-[11.5px] leading-relaxed"
          >
            {tree ? (
              <TreeView node={tree} />
            ) : (
              <span className="text-muted-foreground/40">(waiting…)</span>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </StageFrame>
  );
}

function TreeView({ node, depth = 0 }: { node: TreeNode; depth?: number }) {
  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-baseline gap-1">
        {depth > 0 && (
          <span className="text-muted-foreground/50">
            {"  ".repeat(depth - 1)}└─
          </span>
        )}
        <span
          className={cn(
            depth === 0 ? "text-cyan-200" : "text-foreground/85",
          )}
        >
          {node.label}
        </span>
      </div>
      {node.children?.map((c, i) => (
        <TreeView key={i} node={c} depth={depth + 1} />
      ))}
    </div>
  );
}

// ===================================================================
// VM animation — opcodes execute on a stack.
// ===================================================================

interface VMPhase {
  ip: number;        // pointer into the instruction list (-1 = pre-execution)
  stack: string[];   // top-of-stack last
  env: Record<string, string>;
}

const VM_PROGRAM = [
  "LOAD_CONST 42",
  "STORE_NAME i",
  "LOAD_NAME i",
  "RETURN",
];

const VM_PHASES: VMPhase[] = [
  { ip: -1, stack: [], env: {} },
  { ip: 0, stack: ["42"], env: {} },
  { ip: 1, stack: [], env: { i: "42" } },
  { ip: 2, stack: ["42"], env: { i: "42" } },
  { ip: 3, stack: [], env: { i: "42" } },
];

export function VMAnimation() {
  const phase = usePhase(VM_PHASES.length, 1200);
  const { ip, stack, env } = VM_PHASES[phase];
  return (
    <StageFrame
      label="VM"
      caption="Bytecode runs on a stack machine — same shape as CPython, Lua, or the JVM, just smaller."
      accent="amber"
    >
      <div className="flex gap-3">
        <div className="flex-1">
          <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/70">
            bytecode
          </div>
          <ol className="space-y-0.5">
            {VM_PROGRAM.map((op, i) => {
              const isActive = i === ip;
              return (
                <li
                  key={i}
                  className="flex items-center gap-2 font-mono text-[11.5px]"
                >
                  <span className="w-4 text-right text-muted-foreground/40 tabular-nums">
                    {i}
                  </span>
                  <motion.span
                    animate={{
                      color: isActive ? "#fcd34d" : "rgba(255,255,255,0.65)",
                    }}
                    transition={{ duration: 0.18 }}
                  >
                    {isActive ? "▶" : " "}
                  </motion.span>
                  <motion.span
                    animate={{
                      color: isActive ? "#fcd34d" : "rgba(255,255,255,0.6)",
                    }}
                  >
                    {op}
                  </motion.span>
                </li>
              );
            })}
          </ol>
        </div>
        <div className="w-24">
          <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/70">
            stack
          </div>
          <div className="flex h-[6rem] flex-col-reverse gap-0.5 rounded border border-border/40 bg-background/40 p-1.5">
            <AnimatePresence>
              {stack.map((v, i) => (
                <motion.div
                  key={`${phase}-${i}`}
                  initial={{ opacity: 0, y: -8, scale: 0.9 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -8, scale: 0.9 }}
                  transition={{ duration: 0.18 }}
                  className="rounded border border-amber-500/30 bg-amber-500/10 px-1.5 py-0.5 text-center font-mono text-[11px] text-amber-200 tabular-nums"
                >
                  {v}
                </motion.div>
              ))}
            </AnimatePresence>
            {stack.length === 0 && (
              <span className="self-end text-[9px] uppercase tracking-wider text-muted-foreground/40">
                empty
              </span>
            )}
          </div>
        </div>
      </div>
      <div>
        <div className="mb-1 text-[10px] uppercase tracking-wider text-muted-foreground/70">
          env
        </div>
        <div className="min-h-[1.5rem] rounded border border-border/40 bg-background/40 px-2 py-1 font-mono text-[11.5px]">
          {Object.entries(env).length === 0 ? (
            <span className="text-muted-foreground/40">(empty)</span>
          ) : (
            Object.entries(env).map(([k, v]) => (
              <span key={k} className="mr-3">
                <span className="text-emerald-300">{k}</span>
                <span className="text-muted-foreground">: </span>
                <span className="text-foreground tabular-nums">{v}</span>
              </span>
            ))
          )}
        </div>
      </div>
    </StageFrame>
  );
}
