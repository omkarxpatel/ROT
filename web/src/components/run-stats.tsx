"use client";

import { Activity } from "lucide-react";

import type { AstNode, RotToken } from "@/lib/pyodide-runtime";

interface RunStatsProps {
  tokens: RotToken[];
  ast: AstNode | null;
  output: string;
  source: string;
  timings: { lexMs: number; parseMs: number; interpretMs: number };
}

function countAstNodes(value: unknown): number {
  if (Array.isArray(value)) {
    let sum = 0;
    for (const child of value) sum += countAstNodes(child);
    return sum;
  }
  if (
    value !== null &&
    typeof value === "object" &&
    "__type__" in (value as object)
  ) {
    let sum = 1;
    for (const [k, v] of Object.entries(value as Record<string, unknown>)) {
      if (k === "__type__") continue;
      sum += countAstNodes(v);
    }
    return sum;
  }
  return 0;
}

function formatMs(ms: number): string {
  if (ms >= 100) return `${ms.toFixed(0)} ms`;
  if (ms >= 10) return `${ms.toFixed(1)} ms`;
  if (ms >= 1) return `${ms.toFixed(2)} ms`;
  if (ms > 0) return `${(ms * 1000).toFixed(0)} µs`;
  return "0";
}

function countLines(s: string): number {
  if (s.length === 0) return 0;
  let lines = 0;
  for (const c of s) if (c === "\n") lines++;
  if (!s.endsWith("\n")) lines++;
  return lines;
}

interface StatItem {
  label: string;
  value: string;
  hint?: string;
}

export function RunStats({
  tokens,
  ast,
  output,
  source,
  timings,
}: RunStatsProps) {
  const totalMs = timings.lexMs + timings.parseMs + timings.interpretMs;
  const astNodes = ast ? countAstNodes(ast) : 0;
  const sourceLines = countLines(source);
  const outputLines = countLines(output);

  const items: StatItem[] = [
    {
      label: "total",
      value: formatMs(totalMs),
      hint: "lex + parse + interpret",
    },
    { label: "lex", value: formatMs(timings.lexMs) },
    { label: "parse", value: formatMs(timings.parseMs) },
    { label: "interpret", value: formatMs(timings.interpretMs) },
    { label: "tokens", value: String(tokens.length) },
    { label: "ast nodes", value: String(astNodes) },
    {
      label: "source",
      value: `${sourceLines} line${sourceLines === 1 ? "" : "s"}`,
    },
    {
      label: "output",
      value:
        output.length === 0
          ? "—"
          : `${outputLines} line${outputLines === 1 ? "" : "s"} · ${output.length} char${output.length === 1 ? "" : "s"}`,
    },
  ];

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center gap-2 border-b border-border/60 px-3 py-2 text-xs uppercase tracking-wider text-muted-foreground">
        <Activity className="h-3.5 w-3.5" />
        <span>Run Stats</span>
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 p-3 font-mono text-[12px] sm:grid-cols-4">
        {items.map((item) => (
          <div
            key={item.label}
            className="flex items-baseline gap-2"
            title={item.hint}
          >
            <span className="text-muted-foreground">{item.label}</span>
            <span className="tabular-nums text-foreground">{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
