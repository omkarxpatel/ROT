"use client";

import { motion } from "framer-motion";

import type { RotToken } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface TokensViewProps {
  tokens: RotToken[];
  // Re-mounts the stagger animation when this changes (per Run or per
  // Step in animate mode).
  runKey: number;
  // Optional base delay for the stagger so a multi-stage animation
  // (source → tokens → AST → exec) can offset tokens slightly.
  baseDelaySec?: number;
  // Per-token stagger increment.
  staggerSec?: number;
  // Cap on the number of tokens to apply per-index delay to (avoids a
  // 1000-token program waiting forever). Tokens beyond this index get
  // the cap value.
  staggerCap?: number;
  empty?: string;
}

export function TokensView({
  tokens,
  runKey,
  baseDelaySec = 0,
  staggerSec = 0.04,
  staggerCap = 60,
  empty,
}: TokensViewProps) {
  if (tokens.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        {empty ?? "No tokens yet."}
      </div>
    );
  }
  return (
    <div className="flex flex-wrap gap-1.5">
      {tokens.map((t, i) => (
        <motion.div
          key={`${runKey}-${i}-${t.line}-${t.col}`}
          initial={{ opacity: 0, y: 10, scale: 0.85 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{
            delay: baseDelaySec + Math.min(i, staggerCap) * staggerSec,
            duration: 0.32,
            ease: [0.16, 1, 0.3, 1],
          }}
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

function tokenClass(kind: string): string {
  if (kind === "STRING_LIT" || kind === "F_STRING_LIT") return "chip-string";
  if (kind === "NUMBER_LIT") return "chip-number";
  if (kind === "TRUE" || kind === "FALSE" || kind === "NULL")
    return "chip-literal";
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
  return "chip-keyword";
}

function escapeLexeme(s: string): string {
  if (s === "\n") return "\\n";
  if (s === "\t") return "\\t";
  if (s === " ") return "·";
  return s;
}
