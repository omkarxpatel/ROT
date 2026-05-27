"use client";

import { useCallback, useEffect, useState } from "react";
import { Play, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Editor } from "@/components/editor";
import { ExamplesDropdown } from "@/components/examples-dropdown";
import { OutputPanel } from "@/components/output-panel";
import { PipelinePanel } from "@/components/pipeline-panel";
import { SiteHeader } from "@/components/site-header";
import {
  DEFAULT_EXAMPLE_KEY,
  DEFAULT_EXAMPLE_SOURCE,
} from "@/lib/examples";
import {
  compileAndRun,
  getRuntimeStatus,
  onRuntimeStatus,
  type AstNode,
  type RotError,
  type RotRuntimeStatus,
  type RotToken,
} from "@/lib/pyodide-runtime";

interface PipelineState {
  tokens: RotToken[];
  ast: AstNode | null;
  output: string;
  error: RotError | null;
  trace: string;
  runKey: number;
}

const EMPTY_PIPELINE: PipelineState = {
  tokens: [],
  ast: null,
  output: "",
  error: null,
  trace: "",
  runKey: 0,
};

export default function PlaygroundPage() {
  const [source, setSource] = useState<string>(DEFAULT_EXAMPLE_SOURCE);
  const [currentExample, setCurrentExample] =
    useState<string>(DEFAULT_EXAMPLE_KEY);
  const [running, setRunning] = useState<boolean>(false);
  const [pipeline, setPipeline] = useState<PipelineState>(EMPTY_PIPELINE);
  const [runtimeStatus, setRuntimeStatus] = useState<RotRuntimeStatus>(() =>
    getRuntimeStatus(),
  );

  useEffect(() => {
    return onRuntimeStatus((s) => setRuntimeStatus(s));
  }, []);

  const handleRun = useCallback(async () => {
    if (running) return;
    setRunning(true);
    try {
      const result = await compileAndRun(source);
      const trace = buildTrace(result);
      setPipeline((prev) => ({
        tokens: result.tokens,
        ast: result.ast,
        output: result.output,
        error: result.error,
        trace,
        runKey: prev.runKey + 1,
      }));
    } finally {
      setRunning(false);
    }
  }, [running, source]);

  // Keyboard shortcut: Cmd/Ctrl+Enter to run.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        void handleRun();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleRun]);

  const loadingMessage =
    runtimeStatus.state === "loading"
      ? runtimeStatus.message ?? "loading runtime..."
      : running
        ? "running..."
        : undefined;

  return (
    <div className="flex h-full flex-col">
      <SiteHeader />
      <PlaygroundToolbar
        runtimeStatus={runtimeStatus}
        currentExample={currentExample}
        onSelectExample={(key, src) => {
          setCurrentExample(key);
          setSource(src);
        }}
        running={running}
        onRun={handleRun}
      />
      <main className="flex min-h-0 flex-1 flex-col gap-3 p-3 md:flex-row">
        {/* Left: editor */}
        <section className="flex min-h-[40vh] flex-1 flex-col overflow-hidden rounded-lg border bg-card md:basis-[55%]">
          <div className="border-b border-border/60 px-3 py-2 text-xs uppercase tracking-wider text-muted-foreground">
            Source ({currentExample}.rot)
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <Editor value={source} onChange={setSource} />
          </div>
        </section>
        {/* Right: output (top) + pipeline (bottom) */}
        <section className="flex min-h-[50vh] flex-1 flex-col gap-3 md:basis-[45%]">
          <div className="flex min-h-[24vh] flex-1 flex-col overflow-hidden rounded-lg border bg-card">
            <OutputPanel
              output={pipeline.output}
              error={pipeline.error}
              running={running || runtimeStatus.state === "loading"}
              loadingMessage={loadingMessage}
            />
          </div>
          <div className="flex min-h-[24vh] flex-1 flex-col overflow-hidden rounded-lg border bg-card">
            <PipelinePanel
              tokens={pipeline.tokens}
              ast={pipeline.ast}
              trace={pipeline.trace}
              runKey={pipeline.runKey}
            />
          </div>
        </section>
      </main>
    </div>
  );
}

interface PlaygroundToolbarProps {
  runtimeStatus: RotRuntimeStatus;
  currentExample: string;
  onSelectExample: (key: string, source: string) => void;
  running: boolean;
  onRun: () => void;
}

function PlaygroundToolbar({
  runtimeStatus,
  currentExample,
  onSelectExample,
  running,
  onRun,
}: PlaygroundToolbarProps) {
  return (
    <div className="flex items-center justify-between border-b border-border/60 bg-background/40 px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          Playground
        </span>
        <RuntimeBadge status={runtimeStatus} />
      </div>
      <div className="flex items-center gap-2">
        <ExamplesDropdown
          currentKey={currentExample}
          onSelect={onSelectExample}
        />
        <Button
          size="sm"
          onClick={onRun}
          disabled={running}
          className="gap-1.5"
        >
          {running ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Play className="h-3.5 w-3.5" />
          )}
          Run
          <span className="ml-1 hidden text-[10px] opacity-70 sm:inline">
            {"⌘↵"}
          </span>
        </Button>
      </div>
    </div>
  );
}

function RuntimeBadge({ status }: { status: RotRuntimeStatus }) {
  if (status.state === "idle") {
    return (
      <span className="rounded-full border border-border/60 px-2 py-0.5 text-[10px] uppercase tracking-wider text-muted-foreground">
        runtime: not loaded
      </span>
    );
  }
  if (status.state === "loading") {
    return (
      <span className="inline-flex items-center gap-1 rounded-full border border-amber-500/30 bg-amber-500/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-amber-300">
        <Loader2 className="h-2.5 w-2.5 animate-spin" />
        {status.message ?? "loading"}
      </span>
    );
  }
  if (status.state === "ready") {
    return (
      <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-emerald-300">
        runtime ready
      </span>
    );
  }
  return (
    <span
      className="rounded-full border border-destructive/40 bg-destructive/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-destructive"
      title={status.message}
    >
      runtime error
    </span>
  );
}

function buildTrace(result: {
  output: string;
  error: RotError | null;
  timings: { lexMs: number; parseMs: number; interpretMs: number };
}): string {
  const lines: string[] = [];
  const { lexMs, parseMs, interpretMs } = result.timings;
  lines.push(`lex:       ${lexMs.toFixed(3)} ms`);
  lines.push(`parse:     ${parseMs.toFixed(3)} ms`);
  lines.push(`interpret: ${interpretMs.toFixed(3)} ms`);
  lines.push("");
  if (result.output) {
    lines.push("--- captured stdout ---");
    lines.push(result.output.replace(/\n$/, ""));
  } else {
    lines.push("(no stdout)");
  }
  if (result.error) {
    lines.push("");
    lines.push("--- error ---");
    lines.push(result.error.formatted);
  }
  return lines.join("\n");
}
