"use client";

import { useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { AlertCircle, Eraser, Loader2, Terminal } from "lucide-react";

import { ScrollArea } from "@/components/ui/scroll-area";
import type { RotError } from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

interface OutputPanelProps {
  output: string;
  error: RotError | null;
  running: boolean;
  // Only set when running === true.
  loadingMessage?: string;
  // Optional handler — when provided, the panel renders a Clear button
  // in its header that becomes active whenever there's output or an
  // error to wipe. Pass undefined to hide the button.
  onClear?: () => void;
}

// Streaming rate. ~12ms/char makes ~20-char outputs stream in ~240ms,
// quick enough to keep up with the default Play speed (400ms/step).
// For chunks bigger than the cap, we skip the stream and just snap.
const STREAM_MS_PER_CHAR = 12;
const STREAM_MAX_CHARS = 120;

// Hard cap on the number of output characters we render. A pathological
// loop (e.g. `while (true) { coutln(i) }`) can fill state with megabytes
// of stdout, and rendering one giant <pre> trashes the browser. We slice
// the displayed portion to this cap and append a small "truncated"
// notice. The full string stays in state so the Run Stats card can still
// report the true `output chars` total.
const MAX_DISPLAY_CHARS = 50_000;

// Number formatter for the truncation notice (US locale, thousands
// separators). Reused per-render — cheap to construct but pulling it
// out keeps the JSX clean.
const NUMBER_FORMAT = new Intl.NumberFormat("en-US");

export function OutputPanel({
  output,
  error,
  running,
  loadingMessage,
  onClear,
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
  // Apply the display cap. `displayShown` is what we actually render;
  // `shown` (the full string) is what we use for diffing the new range.
  const exceedsLimit = shown.length > MAX_DISPLAY_CHARS;
  const displayShown = exceedsLimit ? shown.slice(0, MAX_DISPLAY_CHARS) : shown;
  const oldEnd = Math.min(
    newRange?.start ?? displayShown.length,
    displayShown.length,
  );
  // Clip the streaming-new range so we don't render past the cap.
  const visibleNewRange =
    newRange && newRange.start < displayShown.length
      ? { ...newRange, end: Math.min(newRange.end, displayShown.length) }
      : null;

  return (
    <div className="flex h-full flex-col">
      <div className="flex items-center justify-between border-b border-border/60 px-3 py-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wider text-muted-foreground">
          <Terminal className="h-3.5 w-3.5" />
          <span>Output</span>
        </div>
        <div className="flex items-center gap-3">
          {running && (
            <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              <span>{loadingMessage ?? "running..."}</span>
            </div>
          )}
          {!running && onClear && hasContent && (
            <button
              type="button"
              onClick={onClear}
              className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wider text-muted-foreground transition-colors hover:text-foreground"
              title="Clear the output panel"
            >
              <Eraser className="h-3 w-3" />
              <span>Clear</span>
            </button>
          )}
        </div>
      </div>
      <ScrollArea className="min-h-0 flex-1">
        <div className="p-3 font-mono text-[13px] leading-relaxed">
          {!hasContent && !running && (
            <div className="text-muted-foreground">
              Press Run to execute. Output will appear here.
            </div>
          )}
          {!hasContent && running && (
            <RunningBlock message={loadingMessage} />
          )}
          {shown && (
            <pre className="whitespace-pre-wrap text-foreground">
              {/* Old portion — regular foreground color, no animation */}
              {displayShown.slice(0, oldEnd)}
              {/* New portion — starts emerald, fades to foreground via
                  the rot-output-new keyframe. Re-keyed per step so the
                  animation re-fires for each chunk. */}
              {visibleNewRange &&
                displayShown.length > visibleNewRange.start && (
                  <span
                    key={`new-${visibleNewRange.key}`}
                    className="rot-output-new"
                  >
                    {displayShown.slice(
                      visibleNewRange.start,
                      visibleNewRange.end,
                    )}
                  </span>
                )}
            </pre>
          )}
          {exceedsLimit && (
            <div className="mt-2 rounded border border-border/60 bg-muted/30 px-2 py-1.5 text-[11px] text-muted-foreground">
              Output truncated — showing{" "}
              <span className="font-mono tabular-nums text-foreground">
                {NUMBER_FORMAT.format(MAX_DISPLAY_CHARS)}
              </span>{" "}
              of{" "}
              <span className="font-mono tabular-nums text-foreground">
                {NUMBER_FORMAT.format(shown.length)}
              </span>{" "}
              characters. The Run Stats card reports the true total.
            </div>
          )}
          {error && <ErrorBlock error={error} />}
        </div>
      </ScrollArea>
    </div>
  );
}

function RunningBlock({ message }: { message?: string }) {
  // Static — Pyodide.runPython is synchronous and blocks the main
  // thread, so even a CSS-animated spinner won't move during a long
  // run. We still want a clearly visible "we're working on it" cue,
  // so this renders before the block (the page yields one rAF to
  // ensure a paint happens) and then sits frozen until the result
  // arrives.
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="flex flex-col items-start gap-1.5 rounded-md border border-amber-500/30 bg-amber-500/5 p-3"
    >
      <div className="flex items-center gap-2 text-amber-300">
        <Loader2 className="h-3.5 w-3.5 animate-spin" />
        <span className="text-xs uppercase tracking-wider">
          {message ?? "running..."}
        </span>
      </div>
      <span className="text-[11px] text-muted-foreground">
        Long scripts block the UI until the run completes. Output will
        appear here when done.
      </span>
    </motion.div>
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
