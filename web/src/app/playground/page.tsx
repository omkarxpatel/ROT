"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Loader2,
  Pause,
  Play,
  RotateCcw,
  SkipForward,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Editor } from "@/components/editor";
import { ExamplesDropdown } from "@/components/examples-dropdown";
import { OutputPanel } from "@/components/output-panel";
import { PipelinePanel } from "@/components/pipeline-panel";
import { SiteHeader } from "@/components/site-header";
import { StepPanel } from "@/components/step-panel";
import {
  DEFAULT_EXAMPLE_KEY,
  DEFAULT_EXAMPLE_SOURCE,
} from "@/lib/examples";
import {
  compileAndRun,
  compileAndStep,
  getRuntimeStatus,
  onRuntimeStatus,
  type AstNode,
  type RotError,
  type RotRuntimeStatus,
  type RotSnapshot,
  type RotToken,
} from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

type Mode = "run" | "animate";

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

// Default 400ms per auto-step — fast enough to feel responsive, slow
// enough to read what's happening. Slider range is 50ms–2000ms.
const DEFAULT_SPEED_MS = 400;
const MIN_SPEED_MS = 50;
const MAX_SPEED_MS = 2000;

export default function PlaygroundPage() {
  const [source, setSource] = useState<string>(DEFAULT_EXAMPLE_SOURCE);
  const [currentExample, setCurrentExample] =
    useState<string>(DEFAULT_EXAMPLE_KEY);
  const [mode, setMode] = useState<Mode>("run");
  const [running, setRunning] = useState<boolean>(false);
  const [pipeline, setPipeline] = useState<PipelineState>(EMPTY_PIPELINE);
  const [runtimeStatus, setRuntimeStatus] = useState<RotRuntimeStatus>(() =>
    getRuntimeStatus(),
  );

  // Animate-mode state.
  const [snapshots, setSnapshots] = useState<RotSnapshot[]>([]);
  // Source the snapshots were computed for. If the user edits the
  // editor without re-stepping, we'll refetch on the next interaction.
  const [snapshotsSource, setSnapshotsSource] = useState<string>("");
  // -1 means "haven't taken a step yet"; 0..N-1 means "currently at
  // snapshot[i]" (i.e. that statement has just executed).
  const [stepIndex, setStepIndex] = useState<number>(-1);
  const [playing, setPlaying] = useState<boolean>(false);
  const [speedMs, setSpeedMs] = useState<number>(DEFAULT_SPEED_MS);
  const [stepping, setStepping] = useState<boolean>(false);

  useEffect(() => {
    return onRuntimeStatus((s) => setRuntimeStatus(s));
  }, []);

  // --- Run mode ---

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

  // --- Animate mode ---

  const fetchSnapshots = useCallback(async (): Promise<RotSnapshot[]> => {
    setStepping(true);
    try {
      const result = await compileAndStep(source);
      setSnapshots(result.snapshots);
      setSnapshotsSource(source);
      setPipeline((prev) => ({
        tokens: result.tokens,
        ast: result.ast,
        // Run-style aggregate output is the union of every snapshot's
        // captured output; useful for the pipeline trace pane.
        output: result.snapshots.map((s) => s.output_since_last).join(""),
        // Lex/parse errors only — runtime errors live on snapshot.error
        // and surface via the OutputPanel below.
        error: result.error,
        trace: buildStepTrace(result),
        runKey: prev.runKey + 1,
      }));
      return result.snapshots;
    } finally {
      setStepping(false);
    }
  }, [source]);

  // Advance one step. If snapshots are stale (source changed or empty),
  // (re)fetch first, then snap to index 0.
  const handleStep = useCallback(async () => {
    if (stepping) return;
    if (snapshots.length === 0 || source !== snapshotsSource) {
      const fresh = await fetchSnapshots();
      if (fresh.length > 0) setStepIndex(0);
      return;
    }
    setStepIndex((i) => Math.min(i + 1, snapshots.length - 1));
  }, [stepping, snapshots.length, source, snapshotsSource, fetchSnapshots]);

  const handleReset = useCallback(() => {
    setPlaying(false);
    setStepIndex(-1);
    setSnapshots([]);
    setSnapshotsSource("");
  }, []);

  const togglePlay = useCallback(async () => {
    if (playing) {
      setPlaying(false);
      return;
    }
    // If we haven't loaded snapshots yet (or source changed), do that
    // before starting auto-play.
    if (snapshots.length === 0 || source !== snapshotsSource) {
      const fresh = await fetchSnapshots();
      if (fresh.length === 0) return;
      setStepIndex(0);
    }
    setPlaying(true);
  }, [playing, snapshots.length, source, snapshotsSource, fetchSnapshots]);

  // Auto-step loop. Re-scheduled per render when (playing | stepIndex |
  // snapshots.length | speedMs) changes; that gives the speed slider a
  // real-time effect without needing a ref.
  useEffect(() => {
    if (!playing) return;
    if (stepIndex >= snapshots.length - 1) {
      setPlaying(false);
      return;
    }
    const id = window.setTimeout(() => {
      setStepIndex((i) => Math.min(i + 1, snapshots.length - 1));
    }, speedMs);
    return () => window.clearTimeout(id);
  }, [playing, stepIndex, snapshots.length, speedMs]);

  // When the user edits source after a step session, drop stale state
  // so the next Step/Play refetches. We don't auto-fetch here — the
  // user signals intent by clicking.
  useEffect(() => {
    if (snapshots.length > 0 && source !== snapshotsSource) {
      setPlaying(false);
      // Keep snapshots/stepIndex displayed but mark them stale; the
      // next Step/Play will refetch. This avoids a visual flash to
      // empty on every keystroke.
    }
  }, [source, snapshotsSource, snapshots.length]);

  // Switching modes invalidates the "current step" UX but leaves the
  // pipeline display intact so the user can still see tokens/AST.
  const switchMode = useCallback((next: Mode) => {
    setMode(next);
    setPlaying(false);
  }, []);

  // --- Derived state for the OutputPanel ---

  const animateOutput = useMemo(() => {
    if (mode !== "animate" || stepIndex < 0) return "";
    return snapshots
      .slice(0, stepIndex + 1)
      .map((s) => s.output_since_last)
      .join("");
  }, [mode, stepIndex, snapshots]);

  const animateError: RotError | null = useMemo(() => {
    if (mode !== "animate" || stepIndex < 0) return null;
    if (pipeline.error) return pipeline.error;
    const snap = snapshots[stepIndex];
    if (!snap?.error) return null;
    return {
      message: snap.error,
      line: snap.statement_line,
      col: snap.statement_col,
      formatted: snap.error,
      stage: "interpret",
    };
  }, [mode, stepIndex, snapshots, pipeline.error]);

  // Editor line-highlight: in animate mode point at the current
  // snapshot's statement. Null in run mode (no decoration drawn).
  const highlightLine =
    mode === "animate" && stepIndex >= 0
      ? snapshots[stepIndex]?.statement_line ?? null
      : null;

  // Cursor jump request — incremented per click on a token chip so
  // the editor's useEffect re-fires even for repeated jumps to the
  // same coordinates.
  const [editorJumpTo, setEditorJumpTo] = useState<{
    line: number;
    col: number;
    key: number;
  } | null>(null);
  const jumpCounter = useRef(0);
  const handleJumpToSource = useCallback((line: number, col: number) => {
    jumpCounter.current += 1;
    setEditorJumpTo({ line, col, key: jumpCounter.current });
  }, []);

  // Editor's hover-range highlight (sky-blue tint over the line span)
  // driven by mouse hover on AST nodes in the Step panel.
  const [editorHoverRange, setEditorHoverRange] = useState<{
    startLine: number;
    endLine: number;
  } | null>(null);

  const displayOutput = mode === "animate" ? animateOutput : pipeline.output;
  const displayError = mode === "animate" ? animateError : pipeline.error;
  const displayRunning =
    runtimeStatus.state === "loading" ||
    (mode === "run" && running) ||
    (mode === "animate" && stepping);

  // Keyboard shortcut: Cmd/Ctrl+Enter triggers Run or Step depending
  // on mode.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (mode === "run") void handleRun();
        else void handleStep();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, handleRun, handleStep]);

  const loadingMessage =
    runtimeStatus.state === "loading"
      ? runtimeStatus.message ?? "loading runtime..."
      : mode === "animate" && stepping
        ? "stepping..."
        : mode === "run" && running
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
        mode={mode}
        onSwitchMode={switchMode}
        running={running}
        onRun={handleRun}
        snapshots={snapshots}
        stepIndex={stepIndex}
        stepping={stepping}
        playing={playing}
        speedMs={speedMs}
        onSpeedChange={setSpeedMs}
        onStep={handleStep}
        onTogglePlay={togglePlay}
        onReset={handleReset}
      />
      <main className="flex min-h-0 flex-1 flex-col gap-3 p-3 md:flex-row">
        {/* Left: editor */}
        <section className="flex min-h-[40vh] flex-1 flex-col overflow-hidden rounded-lg border bg-card md:basis-[55%]">
          <div className="border-b border-border/60 px-3 py-2 text-xs uppercase tracking-wider text-muted-foreground">
            Source ({currentExample}.rot)
          </div>
          <div className="min-h-0 flex-1 overflow-hidden">
            <Editor
              value={source}
              onChange={setSource}
              highlightLine={highlightLine}
              jumpTo={editorJumpTo}
              hoverRange={editorHoverRange}
            />
          </div>
        </section>
        {/* Right column. In Run mode: Output + Pipeline (2 rows). In
            Animate mode: Output + Env + Pipeline (3 rows) so the
            step-by-step state is visible without scrolling into the
            Pipeline panel. */}
        <section className="flex min-h-[50vh] flex-1 flex-col gap-3 md:basis-[45%]">
          <div className="flex min-h-[20vh] flex-1 flex-col overflow-hidden rounded-lg border bg-card">
            <OutputPanel
              output={displayOutput}
              error={displayError}
              running={displayRunning}
              loadingMessage={loadingMessage}
            />
          </div>
          {mode === "animate" && (
            <div className="flex min-h-[36vh] flex-[1.8] flex-col overflow-hidden rounded-lg border border-amber-500/30 bg-card shadow-[0_0_0_1px_rgba(245,158,11,0.05)]">
              <StepPanel
                source={source}
                tokens={pipeline.tokens}
                ast={pipeline.ast}
                snapshot={
                  stepIndex >= 0 ? snapshots[stepIndex] ?? null : null
                }
                previousSnapshot={
                  stepIndex > 0 ? snapshots[stepIndex - 1] ?? null : null
                }
                stepIndex={stepIndex}
                totalSteps={snapshots.length}
                onJumpToSource={handleJumpToSource}
                onAstHover={setEditorHoverRange}
                playing={playing}
                speedMs={speedMs}
              />
            </div>
          )}
          <div className="flex min-h-[18vh] flex-1 flex-col overflow-hidden rounded-lg border bg-card">
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
  mode: Mode;
  onSwitchMode: (next: Mode) => void;
  running: boolean;
  onRun: () => void;
  snapshots: RotSnapshot[];
  stepIndex: number;
  stepping: boolean;
  playing: boolean;
  speedMs: number;
  onSpeedChange: (ms: number) => void;
  onStep: () => void;
  onTogglePlay: () => void;
  onReset: () => void;
}

function PlaygroundToolbar(props: PlaygroundToolbarProps) {
  const {
    runtimeStatus,
    currentExample,
    onSelectExample,
    mode,
    onSwitchMode,
    running,
    onRun,
    snapshots,
    stepIndex,
    stepping,
    playing,
    speedMs,
    onSpeedChange,
    onStep,
    onTogglePlay,
    onReset,
  } = props;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-background/40 px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          Playground
        </span>
        <RuntimeBadge status={runtimeStatus} />
        <ModeToggle mode={mode} onSwitch={onSwitchMode} />
      </div>
      <div className="flex items-center gap-2">
        <ExamplesDropdown
          currentKey={currentExample}
          onSelect={onSelectExample}
        />
        {mode === "run" ? (
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
        ) : (
          <AnimateControls
            snapshots={snapshots}
            stepIndex={stepIndex}
            stepping={stepping}
            playing={playing}
            speedMs={speedMs}
            onSpeedChange={onSpeedChange}
            onStep={onStep}
            onTogglePlay={onTogglePlay}
            onReset={onReset}
          />
        )}
      </div>
    </div>
  );
}

function ModeToggle({
  mode,
  onSwitch,
}: {
  mode: Mode;
  onSwitch: (next: Mode) => void;
}) {
  return (
    <div className="inline-flex overflow-hidden rounded-md border border-border/60">
      {(["run", "animate"] as Mode[]).map((m) => (
        <button
          key={m}
          type="button"
          onClick={() => onSwitch(m)}
          aria-pressed={mode === m}
          className={cn(
            "px-2 py-0.5 text-[10px] uppercase tracking-wider transition-colors",
            mode === m
              ? "bg-foreground text-background"
              : "bg-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {m}
        </button>
      ))}
    </div>
  );
}

interface AnimateControlsProps {
  snapshots: RotSnapshot[];
  stepIndex: number;
  stepping: boolean;
  playing: boolean;
  speedMs: number;
  onSpeedChange: (ms: number) => void;
  onStep: () => void;
  onTogglePlay: () => void;
  onReset: () => void;
}

function AnimateControls({
  snapshots,
  stepIndex,
  stepping,
  playing,
  speedMs,
  onSpeedChange,
  onStep,
  onTogglePlay,
  onReset,
}: AnimateControlsProps) {
  const hasSnapshots = snapshots.length > 0;
  const atEnd = hasSnapshots && stepIndex >= snapshots.length - 1;
  // Step counter: "0 / 0" before first step; "N / total" after.
  const counter = hasSnapshots
    ? `${Math.max(stepIndex + 1, 1)} / ${snapshots.length}`
    : "— / —";

  return (
    <div className="flex items-center gap-2">
      <span className="hidden font-mono text-[11px] text-muted-foreground sm:inline">
        {counter}
      </span>
      <Button
        size="sm"
        variant="outline"
        onClick={onReset}
        disabled={stepping || !hasSnapshots}
        className="gap-1.5"
        title="Reset to before first step"
      >
        <RotateCcw className="h-3.5 w-3.5" />
        <span className="hidden sm:inline">Reset</span>
      </Button>
      <Button
        size="sm"
        variant="outline"
        onClick={onStep}
        disabled={stepping || (hasSnapshots && atEnd && !playing)}
        className="gap-1.5"
        title="Advance one statement"
      >
        {stepping ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <SkipForward className="h-3.5 w-3.5" />
        )}
        Step
        <span className="ml-1 hidden text-[10px] opacity-70 sm:inline">
          {"⌘↵"}
        </span>
      </Button>
      <Button
        size="sm"
        onClick={onTogglePlay}
        disabled={stepping}
        className="gap-1.5"
        title={playing ? "Pause auto-step" : "Auto-step to end"}
      >
        {playing ? (
          <Pause className="h-3.5 w-3.5" />
        ) : (
          <Play className="h-3.5 w-3.5" />
        )}
        {playing ? "Pause" : "Play"}
      </Button>
      <SpeedSlider value={speedMs} onChange={onSpeedChange} />
    </div>
  );
}

function SpeedSlider({
  value,
  onChange,
}: {
  value: number;
  onChange: (ms: number) => void;
}) {
  // Range is reversed visually: left = slow (long delay), right = fast
  // (short delay). The model value is `ms`. We invert via (MAX+MIN-v).
  const inverted = MAX_SPEED_MS + MIN_SPEED_MS - value;
  return (
    <label className="hidden items-center gap-2 text-[11px] text-muted-foreground sm:inline-flex">
      <span>Speed</span>
      <input
        type="range"
        min={MIN_SPEED_MS}
        max={MAX_SPEED_MS}
        step={50}
        value={inverted}
        onChange={(e) => {
          const v = Number(e.target.value);
          onChange(MAX_SPEED_MS + MIN_SPEED_MS - v);
        }}
        className="h-1 w-24 cursor-pointer appearance-none rounded-full bg-border accent-foreground"
        aria-label="Auto-step speed"
      />
      <span className="font-mono tabular-nums">{value}ms</span>
    </label>
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

function buildStepTrace(result: {
  snapshots: RotSnapshot[];
  error: RotError | null;
  timings: { lexMs: number; parseMs: number; interpretMs: number };
}): string {
  const lines: string[] = [];
  const { lexMs, parseMs, interpretMs } = result.timings;
  lines.push(`lex:       ${lexMs.toFixed(3)} ms`);
  lines.push(`parse:     ${parseMs.toFixed(3)} ms`);
  lines.push(`step-run:  ${interpretMs.toFixed(3)} ms`);
  lines.push("");
  lines.push(`snapshots: ${result.snapshots.length}`);
  if (result.error) {
    lines.push("");
    lines.push("--- error ---");
    lines.push(result.error.formatted);
  }
  return lines.join("\n");
}
