"use client";

import { useCallback, useState } from "react";
import { motion } from "framer-motion";
import {
  AlertCircle,
  ExternalLink,
  Loader2,
  Play,
  RotateCcw,
  Terminal,
} from "lucide-react";

import { CodeBlock } from "@/components/code-block";
import { compileAndRun } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface MiniPlaygroundProps {
  // The fixed program text. No editor — docs control the example.
  source: string;
  // Optional file label rendered above the source (e.g. "demo.rot").
  label?: string;
  // Caption shown above the source — one short sentence about what
  // the example demonstrates.
  caption?: string;
  // Render the output directly with no scroll container. Useful in
  // tight contexts; defaults to a small bounded panel.
  inline?: boolean;
}

// Inline, runnable ROT snippet. Used in docs pages to let readers
// execute the example next to the prose without leaving for the
// playground. Shares the Pyodide singleton — Pyodide is only fetched
// once across the page no matter how many MiniPlaygrounds embed.
export function MiniPlayground({
  source,
  label = "demo.rot",
  caption,
  inline = false,
}: MiniPlaygroundProps) {
  const [output, setOutput] = useState<string>("");
  const [errorText, setErrorText] = useState<string | null>(null);
  const [running, setRunning] = useState<boolean>(false);
  const [ran, setRan] = useState<boolean>(false);

  const handleRun = useCallback(async () => {
    if (running) return;
    setRunning(true);
    // Yield one frame so the loading state paints before pyodide
    // blocks the main thread (same trick the full playground uses).
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => resolve()),
    );
    try {
      const result = await compileAndRun(source);
      setOutput(result.output);
      setErrorText(result.error ? result.error.formatted : null);
      setRan(true);
    } finally {
      setRunning(false);
    }
  }, [source, running]);

  const handleReset = useCallback(() => {
    setOutput("");
    setErrorText(null);
    setRan(false);
  }, []);

  // "Try in playground" URL: base64-encodes the source the same way
  // the playground's Share button does, so links round-trip to the
  // editor cleanly.
  const playgroundHref = encodePlaygroundLink(source);

  return (
    <div className="my-6 overflow-hidden rounded-lg border border-amber-500/20 bg-card/40">
      {caption && (
        <div className="border-b border-border/40 bg-background/40 px-3 py-2 text-[11.5px] leading-snug text-muted-foreground">
          {caption}
        </div>
      )}
      <CodeBlock code={source} language="rot" label={label} />
      <div className="flex flex-wrap items-center justify-between gap-2 border-t border-border/60 bg-background/30 px-3 py-2">
        <div className="flex items-center gap-1.5">
          <button
            type="button"
            onClick={handleRun}
            disabled={running}
            className="inline-flex h-7 items-center gap-1.5 rounded-md bg-amber-500/90 px-2.5 text-[11px] font-medium uppercase tracking-wider text-background transition-colors hover:bg-amber-400 disabled:opacity-60"
          >
            {running ? (
              <Loader2 className="h-3 w-3 animate-spin" />
            ) : (
              <Play className="h-3 w-3" />
            )}
            Run
          </button>
          {ran && (
            <button
              type="button"
              onClick={handleReset}
              disabled={running}
              className="inline-flex h-7 items-center gap-1 rounded-md border border-border/60 px-2 text-[10px] uppercase tracking-wider text-muted-foreground transition-colors hover:bg-accent hover:text-foreground"
            >
              <RotateCcw className="h-3 w-3" />
              Reset
            </button>
          )}
        </div>
        <a
          href={playgroundHref}
          className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground"
          title="Open this code in the full playground"
        >
          Try in playground
          <ExternalLink className="h-3 w-3 opacity-60" />
        </a>
      </div>
      {(ran || running) && (
        <motion.div
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.18 }}
          className="border-t border-border/60"
        >
          <div className="flex items-center gap-1.5 border-b border-border/40 bg-background/20 px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
            <Terminal className="h-3 w-3" />
            Output
          </div>
          <div
            className={cn(
              "px-3 py-2 font-mono text-[12.5px] leading-relaxed",
              !inline && "max-h-[14rem] overflow-auto",
            )}
          >
            {running && !output && !errorText && (
              <span className="flex items-center gap-1.5 text-muted-foreground">
                <Loader2 className="h-3 w-3 animate-spin" />
                running…
              </span>
            )}
            {output && (
              <pre className="whitespace-pre-wrap text-foreground">
                {output}
              </pre>
            )}
            {errorText && (
              <div className="rounded-md border border-destructive/40 bg-destructive/10 px-2 py-1.5">
                <div className="mb-1 flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-destructive">
                  <AlertCircle className="h-3 w-3" />
                  error
                </div>
                <pre className="whitespace-pre-wrap break-words text-[11.5px] text-destructive/90">
                  {errorText}
                </pre>
              </div>
            )}
            {!output && !errorText && !running && (
              <span className="text-muted-foreground">(no output)</span>
            )}
          </div>
        </motion.div>
      )}
    </div>
  );
}

function encodePlaygroundLink(source: string): string {
  // utf-8-safe base64, mirroring the playground's Share button.
  if (typeof window === "undefined") return "/playground";
  try {
    const encoded = btoa(
      encodeURIComponent(source).replace(/%([0-9A-F]{2})/g, (_, p1) =>
        String.fromCharCode(parseInt(p1, 16)),
      ),
    );
    return `/playground?src=${encoded}`;
  } catch {
    return "/playground";
  }
}
