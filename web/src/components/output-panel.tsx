"use client";

import { motion } from "framer-motion";
import { AlertCircle, Loader2, Terminal } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import type { RotError } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface OutputPanelProps {
  output: string;
  error: RotError | null;
  running: boolean;
  // Only set when running === true.
  loadingMessage?: string;
}

export function OutputPanel({
  output,
  error,
  running,
  loadingMessage,
}: OutputPanelProps) {
  const hasContent = Boolean(output) || Boolean(error);
  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border/60 px-3 py-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
          <Terminal className="h-3.5 w-3.5" />
          <span>Output</span>
        </div>
        {running && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>{loadingMessage ?? "running..."}</span>
          </div>
        )}
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-3 font-mono text-[13px] leading-relaxed">
          {!hasContent && !running && (
            <div className="text-muted-foreground">
              Press Run to execute. Output will appear here.
            </div>
          )}
          {output && (
            <motion.pre
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.18 }}
              className="whitespace-pre-wrap text-foreground"
            >
              {output}
            </motion.pre>
          )}
          {error && <ErrorBlock error={error} />}
        </div>
      </ScrollArea>
    </div>
  );
}

function ErrorBlock({ error }: { error: RotError }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className={cn(
        "mt-2 rounded-md border border-destructive/40 bg-destructive/10 p-3",
      )}
    >
      <div className="mb-2 flex items-center gap-2 text-xs uppercase tracking-wider text-destructive">
        <AlertCircle className="h-3.5 w-3.5" />
        <span>{error.stage} error</span>
      </div>
      <pre className="whitespace-pre-wrap break-words text-[12.5px] text-destructive/90">
        {error.formatted}
      </pre>
    </motion.div>
  );
}
