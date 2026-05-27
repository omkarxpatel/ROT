"use client";

import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ChevronRight } from "lucide-react";

import type { AstNode, AstValue } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface AstViewProps {
  ast: AstNode | null;
  // Per-Step / per-Run delay for the root entrance.
  baseDelaySec?: number;
  // Multiplier on depth for the per-node stagger.
  depthStaggerSec?: number;
  empty?: string;
}

export function AstView({
  ast,
  baseDelaySec = 0,
  depthStaggerSec = 0.08,
  empty,
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
      />
    </div>
  );
}

interface AstNodeProps {
  node: AstNode;
  depth: number;
  baseDelaySec: number;
  depthStaggerSec: number;
}

function AstNodeView({
  node,
  depth,
  baseDelaySec,
  depthStaggerSec,
}: AstNodeProps) {
  const [open, setOpen] = useState(true);

  const entries = useMemo(() => {
    const all = Object.entries(node).filter(([k]) => k !== "__type__");
    const inline: [string, string | number | boolean | null | undefined][] = [];
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
  const delay = baseDelaySec + depth * depthStaggerSec;

  return (
    <motion.div
      initial={{ opacity: 0, x: -6 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ delay, duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
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
              <AstValueView
                value={v}
                depth={depth + 1}
                baseDelaySec={baseDelaySec}
                depthStaggerSec={depthStaggerSec}
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
}: {
  value: AstValue;
  depth: number;
  baseDelaySec: number;
  depthStaggerSec: number;
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
          <AstValueView
            key={i}
            value={v}
            depth={depth}
            baseDelaySec={baseDelaySec}
            depthStaggerSec={depthStaggerSec}
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
    />
  );
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
