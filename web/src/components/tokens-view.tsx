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
  // "below" (default): chips slide up into place — subtle, used for
  // the persistent Pipeline panel where tokens just appear.
  // "above": chips fall down from above into place — used by the Step
  // panel so the chips read as falling out of the Source line above
  // them.
  flyFrom?: "below" | "above";
  // Optional pulse signals: when `pulses[i]` changes value, chip `i`
  // fires a one-shot pulse animation (amber ring expanding outward).
  // Used by the Step panel so that when an AST leaf reveals, its
  // source token gets a visible nudge — completing the lex → parse
  // visual link.
  pulses?: Record<number, number>;
}

export function TokensView({
  tokens,
  runKey,
  baseDelaySec = 0,
  staggerSec = 0.04,
  staggerCap = 60,
  empty,
  flyFrom = "below",
  pulses,
}: TokensViewProps) {
  if (tokens.length === 0) {
    return (
      <div className="text-xs text-muted-foreground">
        {empty ?? "No tokens yet."}
      </div>
    );
  }
  const yStart = flyFrom === "above" ? -28 : 10;
  return (
    <div className="flex flex-wrap gap-1">
      {tokens.map((t, i) => {
        const pulseKey = pulses?.[i];
        return (
          <motion.span
            key={`${runKey}-${i}-${t.line}-${t.col}`}
            initial={{ opacity: 0, y: yStart, scale: 0.85 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{
              delay: baseDelaySec + Math.min(i, staggerCap) * staggerSec,
              duration: 0.32,
              ease: [0.16, 1, 0.3, 1],
            }}
            title={`${categoryLabel(t.kind)} (${t.kind.toLowerCase()}) — line ${t.line}:${t.col}`}
            className={cn(
              "relative inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[12px] leading-tight",
              tokenClass(t.kind),
            )}
          >
            {escapeLexeme(t.lexeme)}
            {pulseKey != null && (
              // Overlay ring that scales up and fades on each pulseKey
              // change. Re-keyed by the pulse counter so the same chip
              // can pulse multiple times within one step.
              <motion.span
                key={`pulse-${pulseKey}`}
                initial={{ opacity: 0.9, scale: 0.95 }}
                animate={{ opacity: 0, scale: 1.7 }}
                transition={{ duration: 0.65, ease: "easeOut" }}
                className="pointer-events-none absolute inset-0 rounded ring-2 ring-amber-400"
                aria-hidden
              />
            )}
          </motion.span>
        );
      })}
    </div>
  );
}

// Text-only color (no chip background/border) for inline source-line
// colorization. Mirrors `tokenClass` but strips down to the `text-`
// rule so the colors of the in-source preview match the chip palette.
export function tokenTextColor(kind: string): string {
  const cls = tokenClass(kind);
  switch (cls) {
    case "chip-string":
      return "text-amber-300";
    case "chip-number":
      return "text-cyan-300";
    case "chip-literal":
      return "text-emerald-300";
    case "chip-identifier":
      return "text-sky-300";
    case "chip-operator":
      return "text-rose-300";
    case "chip-punct":
      return "text-zinc-300";
    default:
      return "text-purple-300";
  }
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

// Plain-English category for the tooltip. The category itself is
// already encoded visually via the chip color; this is for hovering
// when the user wants confirmation.
function categoryLabel(kind: string): string {
  const cls = tokenClass(kind);
  switch (cls) {
    case "chip-string":
      return "string";
    case "chip-number":
      return "number";
    case "chip-literal":
      return "literal";
    case "chip-identifier":
      return "name";
    case "chip-punct":
      return "punctuation";
    case "chip-operator":
      return "operator";
    default:
      return "keyword";
  }
}

function escapeLexeme(s: string): string {
  if (s === "\n") return "\\n";
  if (s === "\t") return "\\t";
  if (s === " ") return "·";
  return s;
}
