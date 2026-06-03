"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import {
  ArrowRight,
  Binary,
  Boxes,
  FileCode,
  Hash,
  ScrollText,
  Terminal,
} from "lucide-react";

import { cn } from "@/lib/utils";

interface Stage {
  key: string;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  blurb: string;
  example: string;
  href: string;
  // Used for the subtle per-stage accent color.
  accent: "violet" | "sky" | "emerald" | "amber" | "rose" | "cyan";
}

// Six stages that the playground actually exposes. Order matches the
// real execution order; each `href` deep-links to the corresponding
// internals doc section once those land.
const STAGES: Stage[] = [
  {
    key: "source",
    icon: FileCode,
    label: "Source",
    blurb: "Characters in a file — the program before anything is touched.",
    example: 'coutln("hi")',
    href: "/docs/internals#source",
    accent: "sky",
  },
  {
    key: "tokens",
    icon: Hash,
    label: "Tokens",
    blurb: "A char-by-char lexer turns the source into typed tokens with line + col.",
    example: "coutln · ( · \"hi\" · )",
    href: "/docs/internals#lexer",
    accent: "violet",
  },
  {
    key: "ast",
    icon: Boxes,
    label: "AST",
    blurb: "Recursive-descent for statements; Pratt for expressions. Every node carries source coordinates.",
    example: "Call(coutln, [\"hi\"])",
    href: "/docs/internals#parser",
    accent: "cyan",
  },
  {
    key: "snapshots",
    icon: ScrollText,
    label: "Snapshots",
    blurb: "The tree-walking interpreter executes statements; each one captures an env snapshot.",
    example: "{ i: 1, n: 3 }",
    href: "/docs/internals#interpreter",
    accent: "emerald",
  },
  {
    key: "bytecode",
    icon: Binary,
    label: "Bytecode",
    blurb: "A separate compiler lowers the AST to 38 opcodes that run on a stack VM.",
    example: "LOAD_CONST 1 · STORE_NAME i",
    href: "/docs/internals#bytecode",
    accent: "amber",
  },
  {
    key: "output",
    icon: Terminal,
    label: "Output",
    blurb: "stdout, captured and streamed back to the playground.",
    example: "hi",
    href: "/docs/internals#output",
    accent: "rose",
  },
];

const ACCENT_RING: Record<Stage["accent"], string> = {
  violet: "hover:border-violet-500/40 hover:shadow-[0_0_0_1px_rgba(139,92,246,0.15)]",
  sky: "hover:border-sky-500/40 hover:shadow-[0_0_0_1px_rgba(14,165,233,0.15)]",
  emerald: "hover:border-emerald-500/40 hover:shadow-[0_0_0_1px_rgba(16,185,129,0.15)]",
  amber: "hover:border-amber-500/40 hover:shadow-[0_0_0_1px_rgba(245,158,11,0.15)]",
  rose: "hover:border-rose-500/40 hover:shadow-[0_0_0_1px_rgba(244,63,94,0.15)]",
  cyan: "hover:border-cyan-500/40 hover:shadow-[0_0_0_1px_rgba(6,182,212,0.15)]",
};

const ACCENT_ICON: Record<Stage["accent"], string> = {
  violet: "text-violet-300",
  sky: "text-sky-300",
  emerald: "text-emerald-300",
  amber: "text-amber-300",
  rose: "text-rose-300",
  cyan: "text-cyan-300",
};

export function PipelineDiagram() {
  return (
    <div className="grid gap-3 lg:grid-cols-6 lg:gap-2">
      {STAGES.map((stage, idx) => (
        <PipelineCard key={stage.key} stage={stage} index={idx} />
      ))}
    </div>
  );
}

interface PipelineCardProps {
  stage: Stage;
  index: number;
}

function PipelineCard({ stage, index }: PipelineCardProps) {
  const Icon = stage.icon;
  const isLast = index === STAGES.length - 1;
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-50px" }}
      transition={{ duration: 0.35, delay: index * 0.06 }}
      className="relative"
    >
      <Link
        href={stage.href}
        className={cn(
          "group relative block h-full rounded-lg border border-border/60 bg-card/40 p-4 transition-all",
          ACCENT_RING[stage.accent],
        )}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={cn("h-4 w-4", ACCENT_ICON[stage.accent])} />
            <h3 className="font-mono text-xs uppercase tracking-wider text-foreground">
              {stage.label}
            </h3>
          </div>
          <span className="text-[9px] uppercase tracking-wider text-muted-foreground/60">
            {String(index + 1).padStart(2, "0")}
          </span>
        </div>
        <p className="mt-3 text-[11.5px] leading-relaxed text-muted-foreground">
          {stage.blurb}
        </p>
        <div className="mt-3 rounded border border-border/40 bg-background/40 px-2 py-1 font-mono text-[10.5px] text-foreground/70">
          {stage.example}
        </div>
      </Link>
      {!isLast && (
        <ArrowRight
          aria-hidden
          className="absolute -right-3 top-1/2 hidden h-4 w-4 -translate-y-1/2 text-muted-foreground/30 lg:block"
        />
      )}
    </motion.div>
  );
}
