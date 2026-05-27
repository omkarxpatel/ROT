"use client";

import { useEffect, useRef, useState } from "react";
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

// Streaming rate. ~12ms/char makes ~20-char outputs stream in ~240ms,
// quick enough to keep up with the default Play speed (400ms/step).
// For chunks bigger than the cap, we skip the stream and just snap.
const STREAM_MS_PER_CHAR = 12;
const STREAM_MAX_CHARS = 120;

export function OutputPanel({
  output,
  error,
  running,
  loadingMessage,
}: OutputPanelProps) {
  // What's currently painted in the panel — may lag behind `output`
  // while streaming. After streaming completes, `shown === output`.
  const [shown, setShown] = useState(output);
  // The character range that's currently styled as "new" — fades to
  // the regular text color via CSS animation after it appears.
  const [newRange, setNewRange] = useState<{
    start: number;
    end: number;
    key: number;
  } | null>(null);
  const prevOutputRef = useRef(output);
  const newRangeCounter = useRef(0);

  useEffect(() => {
    if (output === prevOutputRef.current) return;

    // Shrinkage (Reset, or switching examples): sync immediately, no
    // stream, no highlight.
    if (output.length < prevOutputRef.current.length) {
      setShown(output);
      setNewRange(null);
      prevOutputRef.current = output;
      return;
    }

    const newStart = prevOutputRef.current.length;
    const newEnd = output.length;
    const added = newEnd - newStart;
    newRangeCounter.current += 1;
    const key = newRangeCounter.current;

    // Large chunk: skip the stream, but still flash the highlight so
    // the user notices what's new.
    if (added > STREAM_MAX_CHARS) {
      setShown(output);
      setNewRange({ start: newStart, end: newEnd, key });
      prevOutputRef.current = output;
      return;
    }

    // Stream the new chars one at a time.
    setNewRange({ start: newStart, end: newEnd, key });
    let pos = newStart;
    const id = window.setInterval(() => {
      pos += 1;
      if (pos >= newEnd) {
        setShown(output);
        prevOutputRef.current = output;
        window.clearInterval(id);
      } else {
        setShown(output.slice(0, pos));
      }
    }, STREAM_MS_PER_CHAR);
    return () => window.clearInterval(id);
  }, [output]);

  const hasContent = Boolean(shown) || Boolean(error);
  const oldEnd = newRange?.start ?? shown.length;

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
          {shown && (
            <pre className="whitespace-pre-wrap text-foreground">
              {/* Old portion — regular foreground color, no animation */}
              {shown.slice(0, oldEnd)}
              {/* New portion — starts emerald, fades to foreground via
                  the rot-output-new keyframe. Re-keyed per step so the
                  animation re-fires for each chunk. */}
              {newRange && shown.length > newRange.start && (
                <span
                  key={`new-${newRange.key}`}
                  className="rot-output-new"
                >
                  {shown.slice(newRange.start)}
                </span>
              )}
            </pre>
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
