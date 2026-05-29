"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { Pause, Play, RotateCcw, Terminal } from "lucide-react";

import { cn } from "@/lib/utils";

// Hardcoded mini-fizzbuzz trace for n = 3. The animation steps through
// every statement that would execute, mirroring the actual playground
// snapshot model. ~13 seconds at default speed, loops forever.

const SOURCE_LINES = [
  "i = 1",
  "while (i <= 3) {",
  "    if (i == 3) {",
  '        coutln("Fizz")',
  "    } else {",
  "        coutln(i)",
  "    }",
  "    i = i + 1",
  "}",
];

type TokenKind = "kw" | "ident" | "op" | "lit" | "string" | "punct" | "builtin";

interface Token {
  text: string;
  kind: TokenKind;
}

// Per-line token decomposition. Lines that fire in multiple steps reuse
// the same token list — we key everything off the line number so the
// chips are stable as the highlight moves.
const LINE_TOKENS: Record<number, Token[]> = {
  1: [
    { text: "i", kind: "ident" },
    { text: "=", kind: "op" },
    { text: "1", kind: "lit" },
  ],
  2: [
    { text: "while", kind: "kw" },
    { text: "(", kind: "punct" },
    { text: "i", kind: "ident" },
    { text: "<=", kind: "op" },
    { text: "3", kind: "lit" },
    { text: ")", kind: "punct" },
    { text: "{", kind: "punct" },
  ],
  3: [
    { text: "if", kind: "kw" },
    { text: "(", kind: "punct" },
    { text: "i", kind: "ident" },
    { text: "==", kind: "op" },
    { text: "3", kind: "lit" },
    { text: ")", kind: "punct" },
    { text: "{", kind: "punct" },
  ],
  4: [
    { text: "coutln", kind: "builtin" },
    { text: "(", kind: "punct" },
    { text: '"Fizz"', kind: "string" },
    { text: ")", kind: "punct" },
  ],
  6: [
    { text: "coutln", kind: "builtin" },
    { text: "(", kind: "punct" },
    { text: "i", kind: "ident" },
    { text: ")", kind: "punct" },
  ],
  8: [
    { text: "i", kind: "ident" },
    { text: "=", kind: "op" },
    { text: "i", kind: "ident" },
    { text: "+", kind: "op" },
    { text: "1", kind: "lit" },
  ],
};

const TOKEN_COLORS: Record<TokenKind, string> = {
  kw: "text-violet-300 bg-violet-500/10 border-violet-500/30",
  ident: "text-sky-200 bg-sky-500/5 border-sky-500/20",
  op: "text-amber-200 bg-amber-500/10 border-amber-500/30",
  lit: "text-emerald-200 bg-emerald-500/10 border-emerald-500/30",
  string: "text-amber-300 bg-amber-500/10 border-amber-500/30",
  punct: "text-muted-foreground bg-muted/30 border-border/60",
  builtin: "text-sky-300 bg-sky-500/10 border-sky-500/30",
};

interface Step {
  line: number;
  ast: string;
  // Optional "Run" details. Mutually-ish exclusive but the type allows
  // both (e.g. a Call that produces output + a binding update).
  run: {
    binding?: { name: string; value: string };
    cond?: { expr: string; result: "true" | "false" };
    callOutput?: string;
  };
  // Cumulative output line appended this step. Used to derive what's
  // visible in the Output panel without recomputing every render.
  outputDelta?: string;
}

const STEPS: Step[] = [
  {
    line: 1,
    ast: "Assign(i, 1)",
    run: { binding: { name: "i", value: "1" } },
  },
  {
    line: 2,
    ast: "While(cond, body)",
    run: { cond: { expr: "1 <= 3", result: "true" } },
  },
  {
    line: 3,
    ast: "If(cond, then, else)",
    run: { cond: { expr: "1 == 3", result: "false" } },
  },
  {
    line: 6,
    ast: "Call(coutln, [i])",
    run: { callOutput: "1" },
    outputDelta: "1\n",
  },
  {
    line: 8,
    ast: "Assign(i, BinOp(+, i, 1))",
    run: { binding: { name: "i", value: "2" } },
  },
  {
    line: 2,
    ast: "While(cond, body)",
    run: { cond: { expr: "2 <= 3", result: "true" } },
  },
  {
    line: 3,
    ast: "If(cond, then, else)",
    run: { cond: { expr: "2 == 3", result: "false" } },
  },
  {
    line: 6,
    ast: "Call(coutln, [i])",
    run: { callOutput: "2" },
    outputDelta: "2\n",
  },
  {
    line: 8,
    ast: "Assign(i, BinOp(+, i, 1))",
    run: { binding: { name: "i", value: "3" } },
  },
  {
    line: 2,
    ast: "While(cond, body)",
    run: { cond: { expr: "3 <= 3", result: "true" } },
  },
  {
    line: 3,
    ast: "If(cond, then, else)",
    run: { cond: { expr: "3 == 3", result: "true" } },
  },
  {
    line: 4,
    ast: 'Call(coutln, ["Fizz"])',
    run: { callOutput: "Fizz" },
    outputDelta: "Fizz\n",
  },
  {
    line: 8,
    ast: "Assign(i, BinOp(+, i, 1))",
    run: { binding: { name: "i", value: "4" } },
  },
  {
    line: 2,
    ast: "While(cond, body)",
    run: { cond: { expr: "4 <= 3", result: "false" } },
  },
];

// 950ms per step keeps the loop ~13s long. Slow enough to read, fast
// enough to feel alive without dragging.
const STEP_MS = 950;
// Brief pause at the end before looping back to step 0 so the viewer
// reads the final output before it disappears.
const LOOP_PAUSE_MS = 1800;

export function HeroAnimation() {
  const [stepIndex, setStepIndex] = useState(0);
  const [playing, setPlaying] = useState(true);

  useEffect(() => {
    if (!playing) return;
    const isLast = stepIndex >= STEPS.length - 1;
    const id = window.setTimeout(
      () => {
        if (isLast) setStepIndex(0);
        else setStepIndex((i) => i + 1);
      },
      isLast ? LOOP_PAUSE_MS : STEP_MS,
    );
    return () => window.clearTimeout(id);
  }, [stepIndex, playing]);

  const step = STEPS[stepIndex];
  const tokens = LINE_TOKENS[step.line] ?? [];

  // Cumulative output: every prior step's delta concatenated. Cheap to
  // recompute per render given the small step count.
  const cumulativeOutput = useMemo(() => {
    let acc = "";
    for (let i = 0; i <= stepIndex; i++) {
      if (STEPS[i].outputDelta) acc += STEPS[i].outputDelta;
    }
    return acc;
  }, [stepIndex]);

  return (
    <div className="relative rounded-lg border border-border/60 bg-card/50 p-4 shadow-[0_0_0_1px_rgba(245,158,11,0.04)]">
      <Toolbar
        stepIndex={stepIndex}
        playing={playing}
        onTogglePlay={() => setPlaying((p) => !p)}
        onReset={() => {
          setStepIndex(0);
          setPlaying(true);
        }}
      />
      <div className="mt-3 grid gap-3 lg:grid-cols-5">
        <div className="lg:col-span-3">
          <SourcePanel activeLine={step.line} />
        </div>
        <div className="flex flex-col gap-3 lg:col-span-2">
          <OutputPanel output={cumulativeOutput} />
        </div>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <ReadCard tokens={tokens} stepKey={stepIndex} />
        <ParseCard astLabel={step.ast} stepKey={stepIndex} />
        <RunCard run={step.run} stepKey={stepIndex} />
      </div>
    </div>
  );
}

interface ToolbarProps {
  stepIndex: number;
  playing: boolean;
  onTogglePlay: () => void;
  onReset: () => void;
}

function Toolbar({ stepIndex, playing, onTogglePlay, onReset }: ToolbarProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wider text-muted-foreground">
          Live demo
        </span>
        <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
          step {stepIndex + 1}/{STEPS.length}
        </span>
      </div>
      <div className="flex items-center gap-1">
        <button
          type="button"
          onClick={onReset}
          className="inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-[10px] uppercase tracking-wider text-muted-foreground hover:bg-accent hover:text-foreground"
          title="Restart"
        >
          <RotateCcw className="h-3 w-3" />
        </button>
        <button
          type="button"
          onClick={onTogglePlay}
          className="inline-flex h-6 items-center gap-1 rounded-md px-1.5 text-[10px] uppercase tracking-wider text-muted-foreground hover:bg-accent hover:text-foreground"
          title={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <Pause className="h-3 w-3" />
          ) : (
            <Play className="h-3 w-3" />
          )}
        </button>
      </div>
    </div>
  );
}

function SourcePanel({ activeLine }: { activeLine: number }) {
  return (
    <div className="overflow-hidden rounded-md border border-border/60 bg-background/60">
      <div className="border-b border-border/60 px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        Source
      </div>
      <pre className="overflow-x-auto p-3 font-mono text-[12.5px] leading-[1.7]">
        {SOURCE_LINES.map((line, idx) => {
          const lineNum = idx + 1;
          const isActive = lineNum === activeLine;
          return (
            <div
              key={lineNum}
              className={cn(
                "relative flex items-center gap-3 -mx-3 px-3 transition-colors",
                isActive && "bg-amber-500/10",
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="source-active-bar"
                  className="absolute left-0 top-0 h-full w-[2px] bg-amber-400"
                  transition={{ type: "spring", stiffness: 500, damping: 40 }}
                />
              )}
              <span className="w-6 select-none text-right text-[10px] text-muted-foreground/60 tabular-nums">
                {lineNum}
              </span>
              <span
                className={cn(
                  "whitespace-pre",
                  isActive ? "text-foreground" : "text-foreground/55",
                )}
              >
                {line}
              </span>
            </div>
          );
        })}
      </pre>
    </div>
  );
}

function OutputPanel({ output }: { output: string }) {
  return (
    <div className="flex h-full flex-col overflow-hidden rounded-md border border-border/60 bg-background/60">
      <div className="flex items-center gap-1.5 border-b border-border/60 px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        <Terminal className="h-3 w-3" />
        Output
      </div>
      <div className="min-h-[8rem] flex-1 p-3 font-mono text-[12.5px] leading-relaxed">
        {output.length === 0 ? (
          <span className="text-muted-foreground/40">(waiting…)</span>
        ) : (
          <pre className="whitespace-pre-wrap text-foreground">{output}</pre>
        )}
      </div>
    </div>
  );
}

interface ReadCardProps {
  tokens: Token[];
  stepKey: number;
}

function ReadCard({ tokens, stepKey }: ReadCardProps) {
  return (
    <StageCard label="Read" hint="tokens">
      <div className="flex flex-wrap items-center gap-1">
        <AnimatePresence mode="popLayout">
          {tokens.map((t, i) => (
            <motion.span
              key={`${stepKey}-${i}-${t.text}`}
              initial={{ opacity: 0, y: -4, scale: 0.85 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 4, scale: 0.85 }}
              transition={{
                delay: i * 0.05,
                duration: 0.22,
                ease: "easeOut",
              }}
              className={cn(
                "rounded border px-1.5 py-0.5 font-mono text-[11px]",
                TOKEN_COLORS[t.kind],
              )}
            >
              {t.text}
            </motion.span>
          ))}
        </AnimatePresence>
      </div>
    </StageCard>
  );
}

interface ParseCardProps {
  astLabel: string;
  stepKey: number;
}

function ParseCard({ astLabel, stepKey }: ParseCardProps) {
  return (
    <StageCard label="Parse" hint="ast node">
      <AnimatePresence mode="wait">
        <motion.div
          key={stepKey}
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="font-mono text-[11.5px] text-sky-200/90"
        >
          {astLabel}
        </motion.div>
      </AnimatePresence>
    </StageCard>
  );
}

interface RunCardProps {
  run: Step["run"];
  stepKey: number;
}

function RunCard({ run, stepKey }: RunCardProps) {
  return (
    <StageCard label="Run" hint="effect">
      <AnimatePresence mode="wait">
        <motion.div
          key={stepKey}
          initial={{ opacity: 0, scale: 0.97 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          className="space-y-1 font-mono text-[11.5px]"
        >
          {run.binding && (
            <div className="flex items-baseline gap-1.5">
              <span className="text-emerald-300">{run.binding.name}</span>
              <span className="text-muted-foreground">←</span>
              <span className="text-foreground tabular-nums">
                {run.binding.value}
              </span>
            </div>
          )}
          {run.cond && (
            <div className="flex flex-wrap items-baseline gap-1.5">
              <span className="text-muted-foreground">{run.cond.expr}</span>
              <span className="text-muted-foreground">⇒</span>
              <span
                className={cn(
                  "rounded px-1 py-0.5 text-[10px] tabular-nums",
                  run.cond.result === "true"
                    ? "bg-emerald-500/15 text-emerald-300"
                    : "bg-rose-500/15 text-rose-300",
                )}
              >
                {run.cond.result}
              </span>
            </div>
          )}
          {run.callOutput && (
            <div className="flex items-baseline gap-1.5">
              <span className="text-muted-foreground">print</span>
              <span className="text-muted-foreground">→</span>
              <span className="text-emerald-300">{run.callOutput}</span>
            </div>
          )}
        </motion.div>
      </AnimatePresence>
    </StageCard>
  );
}

interface StageCardProps {
  label: string;
  hint: string;
  children: React.ReactNode;
}

function StageCard({ label, hint, children }: StageCardProps) {
  return (
    <div className="rounded-md border border-border/60 bg-background/60 px-3 py-2">
      <div className="mb-1.5 flex items-baseline justify-between">
        <span className="text-[10px] uppercase tracking-wider text-foreground/80">
          {label}
        </span>
        <span className="text-[9px] uppercase tracking-wider text-muted-foreground/70">
          {hint}
        </span>
      </div>
      <div className="min-h-[2.5rem]">{children}</div>
    </div>
  );
}
