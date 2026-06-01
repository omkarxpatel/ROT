"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  Check,
  Compass,
  Link2,
  Loader2,
  Pause,
  Play,
  RotateCcw,
  SkipForward,
} from "lucide-react";
import { AnimatePresence, motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { BytecodeView } from "@/components/bytecode-view";
import { Editor } from "@/components/editor";
import { ExamplesDropdown } from "@/components/examples-dropdown";
import { OutputPanel } from "@/components/output-panel";
import { RunStats } from "@/components/run-stats";
import { SiteHeader } from "@/components/site-header";
import {
  SnapshotTimeline,
  type TimelineEntry,
} from "@/components/snapshot-timeline";
import { StepPanel } from "@/components/step-panel";
import { VMStepPanel } from "@/components/vm-step-panel";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  DEFAULT_EXAMPLE_KEY,
  DEFAULT_EXAMPLE_SOURCE,
  loadExamples,
} from "@/lib/examples";
import { TOURS, captionFor, findTour, type Tour } from "@/lib/tours";
import {
  compileAndRun,
  compileAndStep,
  compileAndStepVM,
  compileToChunk,
  getRuntimeStatus,
  onRuntimeStatus,
  type AstNode,
  type RotChunkDump,
  type RotError,
  type RotRuntimeStatus,
  type RotSnapshot,
  type RotToken,
  type RotVMSnapshot,
} from "@/lib/pyodide-runtime";
import { cn } from "@/lib/utils";

type Mode = "run" | "animate";
type Engine = "tree-walker" | "vm";

interface PipelineState {
  tokens: RotToken[];
  ast: AstNode | null;
  output: string;
  error: RotError | null;
  runKey: number;
  // Set on Run; carried into RunStats below the Output panel. Stays at
  // zeros before the first run.
  timings: { lexMs: number; parseMs: number; interpretMs: number };
}

const EMPTY_PIPELINE: PipelineState = {
  tokens: [],
  ast: null,
  output: "",
  error: null,
  runKey: 0,
  timings: { lexMs: 0, parseMs: 0, interpretMs: 0 },
};

// Default 400ms per auto-step — fast enough to feel responsive, slow
// enough to read what's happening. Slider range is 50ms–2000ms.
const DEFAULT_SPEED_MS = 400;
const MIN_SPEED_MS = 50;
const MAX_SPEED_MS = 2000;

// localStorage key used to persist the editor's source across page
// reloads.
const LS_SOURCE_KEY = "rot-playground:source";

// Read URL + localStorage for an alternate initial source. Returns
// null when neither is set — the page should fall back to the
// bundled default. Browser-only (called from useEffect).
function readClientStoredSource(): string | null {
  try {
    const params = new URLSearchParams(window.location.search);
    const src = params.get("src");
    if (src) {
      // base64 → utf-8. atob alone doesn't round-trip non-ASCII; use
      // the standard decode-via-percent-encoding trick.
      return decodeURIComponent(
        atob(src)
          .split("")
          .map((c) => `%${("00" + c.charCodeAt(0).toString(16)).slice(-2)}`)
          .join(""),
      );
    }
  } catch {
    // bad ?src= — fall through.
  }
  try {
    const stored = window.localStorage.getItem(LS_SOURCE_KEY);
    if (stored && stored.length > 0) return stored;
  } catch {
    // localStorage blocked — fall through.
  }
  return null;
}

export default function PlaygroundPage() {
  // First render must be deterministic across server and client to
  // avoid a hydration mismatch: SSR has no `window`, so the URL +
  // localStorage check below was returning DEFAULT on the server
  // and the URL-derived value on the client. We now initialize to
  // the bundled default on BOTH, then swap in a useEffect after
  // mount.
  const [source, setSource] = useState<string>(DEFAULT_EXAMPLE_SOURCE);
  // Loaded example sources keyed by example name. Used to detect which
  // example (if any) the current editor source matches — that drives
  // the dropdown selection and the SOURCE (xxx.rot) label.
  const [examplesByKey, setExamplesByKey] = useState<Record<string, string>>(
    () => ({ [DEFAULT_EXAMPLE_KEY]: DEFAULT_EXAMPLE_SOURCE }),
  );
  // After mount, check URL / localStorage and switch source if
  // there's a saved or shared one. Runs once (empty deps).
  useEffect(() => {
    const found = readClientStoredSource();
    if (found !== null) setSource(found);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  // Load every example's source so we can identify which one (if any)
  // the current source matches. Also handle `?example=<key>` deep
  // links from the homepage Demos cards — we resolve the key once the
  // sources are in hand. `?src=` (handled above) wins over `?example=`
  // if both are present.
  useEffect(() => {
    let cancelled = false;
    loadExamples()
      .then((e) => {
        if (cancelled) return;
        setExamplesByKey(e);
        try {
          const params = new URLSearchParams(window.location.search);
          // `?src=` was already applied in the first useEffect; don't
          // clobber it here.
          if (params.get("src")) return;
          const key = params.get("example");
          if (key && e[key]) setSource(e[key]);
        } catch {
          // bad URL — leave source as-is.
        }
      })
      .catch(() => {
        // Non-fatal: fall back to the bundled default for matching.
      });
    return () => {
      cancelled = true;
    };
  }, []);
  // Derive the current example from the source. If the source matches
  // a known example exactly, show that example's key; otherwise show
  // "custom". This way the dropdown stays in sync with the editor no
  // matter how the source got there (default, URL, localStorage, user
  // selection, hand edit).
  const currentExample = useMemo(() => {
    for (const [key, src] of Object.entries(examplesByKey)) {
      if (src === source) return key;
    }
    return "custom";
  }, [source, examplesByKey]);
  const [mode, setMode] = useState<Mode>("run");
  const [running, setRunning] = useState<boolean>(false);
  const [pipeline, setPipeline] = useState<PipelineState>(EMPTY_PIPELINE);
  const [runtimeStatus, setRuntimeStatus] = useState<RotRuntimeStatus>(() =>
    getRuntimeStatus(),
  );

  // Tour state. When a tour key is set, the playground:
  //   - loads the tour's source
  //   - flips to Animate mode
  //   - uses the tour's suggested speed
  //   - renders a caption banner above Step Detail
  // Editing the source (or selecting an example) clears the tour.
  const [tourKey, setTourKey] = useState<string | null>(null);
  const activeTour = useMemo(() => findTour(tourKey), [tourKey]);
  // Tour stays "active" only while the editor source still matches the
  // tour's program. If the user types into the editor, the tour bails
  // out (a useEffect below handles this — defensive double-check here).
  const tourEffective = activeTour && activeTour.source === source
    ? activeTour
    : null;

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

  // M3 — engine toggle for animate mode. Tree-walker is the default
  // (statement-level snapshots, the original v2.26 path); VM swaps
  // in opcode-level snapshots from the bytecode VM. State for each
  // engine lives side-by-side so flipping back and forth doesn't
  // re-fetch.
  const [engine, setEngine] = useState<Engine>("tree-walker");
  const [vmSnapshots, setVmSnapshots] = useState<RotVMSnapshot[]>([]);
  const [vmChunksById, setVmChunksById] = useState<Record<string, RotChunkDump>>(
    {},
  );
  const [vmSnapshotsSource, setVmSnapshotsSource] = useState<string>("");
  // Currently active list length — used to bound stepIndex math
  // engine-agnostically.
  const activeSnapshotCount =
    engine === "vm" ? vmSnapshots.length : snapshots.length;

  useEffect(() => {
    return onRuntimeStatus((s) => setRuntimeStatus(s));
  }, []);

  // Persist source to localStorage with a small debounce so we don't
  // hit storage on every keystroke. 400ms is short enough to feel
  // immediate to the user but groups typing bursts.
  useEffect(() => {
    if (typeof window === "undefined") return;
    const id = window.setTimeout(() => {
      try {
        window.localStorage.setItem(LS_SOURCE_KEY, source);
      } catch {
        // storage quota / private mode — silent.
      }
    }, 400);
    return () => window.clearTimeout(id);
  }, [source]);

  // Share-by-URL: build a `?src=<base64>` link, copy to clipboard,
  // show a brief "copied" pill on the button.
  const [shareState, setShareState] = useState<"idle" | "copied" | "error">(
    "idle",
  );
  const handleShare = useCallback(async () => {
    try {
      // utf-8-safe base64: percent-encode each character first, then
      // btoa the resulting ascii.
      const encoded = btoa(
        encodeURIComponent(source).replace(/%([0-9A-F]{2})/g, (_, p1) =>
          String.fromCharCode(parseInt(p1, 16)),
        ),
      );
      const url = new URL(window.location.href);
      url.searchParams.set("src", encoded);
      // Update the address bar so reloads keep the shared source —
      // history.replaceState avoids polluting the back stack.
      window.history.replaceState({}, "", url.toString());
      await navigator.clipboard.writeText(url.toString());
      setShareState("copied");
      window.setTimeout(() => setShareState("idle"), 1800);
    } catch {
      setShareState("error");
      window.setTimeout(() => setShareState("idle"), 1800);
    }
  }, [source]);

  // --- Run mode ---

  const handleRun = useCallback(async () => {
    if (running) return;
    setRunning(true);
    // Yield one animation frame so React paints `running=true` BEFORE
    // pyodide.runPython (which is synchronous) blocks the main thread.
    // Without this, long scripts freeze the UI on the pre-run state and
    // the user never sees a loading indicator.
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => resolve()),
    );
    try {
      const result = await compileAndRun(source);
      setPipeline((prev) => ({
        tokens: result.tokens,
        ast: result.ast,
        output: result.output,
        error: result.error,
        runKey: prev.runKey + 1,
        timings: result.timings,
      }));
    } finally {
      setRunning(false);
    }
  }, [running, source]);

  // Clear the Output panel — wipes output/error/timings and resets
  // runKey so the RunStats card hides until the next Run. Source is
  // untouched; the editor keeps whatever the user has there.
  const handleClearOutput = useCallback(() => {
    setPipeline(EMPTY_PIPELINE);
  }, []);

  // --- Tour mode ---

  // Start a tour: load its source, flip to Animate, set its speed,
  // drop stale step state so the next Play fetches fresh snapshots.
  const handleStartTour = useCallback((tour: Tour) => {
    setSource(tour.source);
    setMode("animate");
    setSpeedMs(tour.speedMs ?? 900);
    setTourKey(tour.key);
    setSnapshots([]);
    setSnapshotsSource("");
    setStepIndex(-1);
    setPlaying(false);
  }, []);

  // Auto-bail: if the user edits the source so it no longer matches
  // the tour's program, clear the tour. We don't show a warning;
  // selecting a tour again restores it.
  useEffect(() => {
    if (!activeTour) return;
    if (source !== activeTour.source) setTourKey(null);
  }, [source, activeTour]);

  // --- Animate mode ---

  const fetchVMSnapshots = useCallback(async (): Promise<RotVMSnapshot[]> => {
    setStepping(true);
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => resolve()),
    );
    try {
      const result = await compileAndStepVM(source);
      setVmSnapshots(result.snapshots);
      setVmChunksById(result.chunks_by_id);
      setVmSnapshotsSource(source);
      setPipeline((prev) => ({
        tokens: result.tokens,
        // VM mode skips the AST view — the rendered chunk replaces it.
        ast: null,
        output: result.snapshots
          .map((s) => s.output_since_last)
          .join(""),
        error: result.error,
        runKey: prev.runKey + 1,
        timings: {
          lexMs: result.timings.lexMs,
          parseMs: result.timings.parseMs,
          // Best-shape mapping: report compile+run as the interpret
          // bar in the Run Stats card.
          interpretMs:
            result.timings.compileMs + result.timings.runMs,
        },
      }));
      return result.snapshots;
    } finally {
      setStepping(false);
    }
  }, [source]);

  const fetchSnapshots = useCallback(async (): Promise<RotSnapshot[]> => {
    setStepping(true);
    // Same rAF yield as handleRun — let the "stepping..." indicator
    // paint before pyodide.runPython blocks the main thread on large
    // programs (e.g. a loop that produces hundreds of snapshots).
    await new Promise<void>((resolve) =>
      requestAnimationFrame(() => resolve()),
    );
    try {
      const result = await compileAndStep(source);
      setSnapshots(result.snapshots);
      setSnapshotsSource(source);
      setPipeline((prev) => ({
        tokens: result.tokens,
        ast: result.ast,
        // Aggregate output is the union of every snapshot's captured
        // output — shown in the Output panel.
        output: result.snapshots.map((s) => s.output_since_last).join(""),
        // Lex/parse errors only — runtime errors live on snapshot.error
        // and surface via the OutputPanel below.
        error: result.error,
        runKey: prev.runKey + 1,
        timings: result.timings,
      }));
      return result.snapshots;
    } finally {
      setStepping(false);
    }
  }, [source]);

  // Advance one step. If snapshots are stale (source changed or empty),
  // (re)fetch first, then snap to index 0. Dispatches on `engine` so
  // tree-walker and VM each fetch from their own bridge function.
  const handleStep = useCallback(async () => {
    if (stepping) return;
    if (engine === "vm") {
      if (vmSnapshots.length === 0 || source !== vmSnapshotsSource) {
        const fresh = await fetchVMSnapshots();
        if (fresh.length > 0) setStepIndex(0);
        return;
      }
      setStepIndex((i) => Math.min(i + 1, vmSnapshots.length - 1));
      return;
    }
    if (snapshots.length === 0 || source !== snapshotsSource) {
      const fresh = await fetchSnapshots();
      if (fresh.length > 0) setStepIndex(0);
      return;
    }
    setStepIndex((i) => Math.min(i + 1, snapshots.length - 1));
  }, [
    stepping,
    engine,
    snapshots.length,
    snapshotsSource,
    vmSnapshots.length,
    vmSnapshotsSource,
    source,
    fetchSnapshots,
    fetchVMSnapshots,
  ]);

  const handleReset = useCallback(() => {
    setPlaying(false);
    setStepIndex(-1);
    setSnapshots([]);
    setSnapshotsSource("");
    setVmSnapshots([]);
    setVmChunksById({});
    setVmSnapshotsSource("");
  }, []);

  const togglePlay = useCallback(async () => {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (engine === "vm") {
      if (vmSnapshots.length === 0 || source !== vmSnapshotsSource) {
        const fresh = await fetchVMSnapshots();
        if (fresh.length === 0) return;
        setStepIndex(0);
      }
      setPlaying(true);
      return;
    }
    if (snapshots.length === 0 || source !== snapshotsSource) {
      const fresh = await fetchSnapshots();
      if (fresh.length === 0) return;
      setStepIndex(0);
    }
    setPlaying(true);
  }, [
    playing,
    engine,
    snapshots.length,
    snapshotsSource,
    vmSnapshots.length,
    vmSnapshotsSource,
    source,
    fetchSnapshots,
    fetchVMSnapshots,
  ]);

  // Switching engine drops stale step state and restarts the
  // counter — the two engines' snapshot lists aren't aligned so
  // sharing stepIndex across them would land on nonsense.
  const handleEngineChange = useCallback((next: Engine) => {
    setEngine(next);
    setPlaying(false);
    setStepIndex(-1);
  }, []);

  // Auto-step loop. Re-scheduled per render when (playing, stepIndex,
  // snapshots, speedMs) changes; that gives the speed slider a
  // real-time effect without needing a ref. Also halts Play when the
  // current snapshot carries an error — the user can Step manually
  // past it (if there's anything left) and click Play to continue.
  useEffect(() => {
    if (!playing) return;
    const total = activeSnapshotCount;
    if (stepIndex >= total - 1) {
      setPlaying(false);
      return;
    }
    const errorAtCurrent =
      engine === "vm"
        ? vmSnapshots[stepIndex]?.error
        : snapshots[stepIndex]?.error;
    if (errorAtCurrent) {
      setPlaying(false);
      return;
    }
    const id = window.setTimeout(() => {
      setStepIndex((i) => Math.min(i + 1, total - 1));
    }, speedMs);
    return () => window.clearTimeout(id);
  }, [playing, engine, stepIndex, snapshots, vmSnapshots, activeSnapshotCount, speedMs]);

  // When the user edits source after a step session, drop stale state
  // so the next Step/Play refetches. We don't auto-fetch here — the
  // user signals intent by clicking.
  useEffect(() => {
    const sourceMatch =
      engine === "vm"
        ? source === vmSnapshotsSource
        : source === snapshotsSource;
    if (activeSnapshotCount > 0 && !sourceMatch) {
      setPlaying(false);
    }
  }, [
    engine,
    source,
    snapshotsSource,
    vmSnapshotsSource,
    activeSnapshotCount,
  ]);

  // Switching modes invalidates the "current step" UX but leaves the
  // pipeline display intact so the user can still see tokens/AST.
  const switchMode = useCallback((next: Mode) => {
    setMode(next);
    setPlaying(false);
  }, []);

  // --- Derived state for the OutputPanel ---

  const animateOutput = useMemo(() => {
    if (mode !== "animate" || stepIndex < 0) return "";
    if (engine === "vm") {
      return vmSnapshots
        .slice(0, stepIndex + 1)
        .map((s) => s.output_since_last)
        .join("");
    }
    return snapshots
      .slice(0, stepIndex + 1)
      .map((s) => s.output_since_last)
      .join("");
  }, [mode, engine, stepIndex, snapshots, vmSnapshots]);

  const animateError: RotError | null = useMemo(() => {
    if (mode !== "animate" || stepIndex < 0) return null;
    if (pipeline.error) return pipeline.error;
    if (engine === "vm") {
      const snap = vmSnapshots[stepIndex];
      if (!snap?.error) return null;
      return {
        message: snap.error,
        line: snap.line,
        col: 0,
        formatted: snap.error,
        stage: "interpret",
      };
    }
    const snap = snapshots[stepIndex];
    if (!snap?.error) return null;
    return {
      message: snap.error,
      line: snap.statement_line,
      col: snap.statement_col,
      formatted: snap.error,
      stage: "interpret",
    };
  }, [mode, engine, stepIndex, snapshots, vmSnapshots, pipeline.error]);

  // Editor line-highlight: in animate mode point at the current
  // snapshot's statement (tree-walker) or the source line that
  // produced the current opcode (VM). Null in run mode.
  const highlightLine = useMemo(() => {
    if (mode !== "animate" || stepIndex < 0) return null;
    if (engine === "vm") {
      const snap = vmSnapshots[stepIndex];
      return snap?.line || null;
    }
    return snapshots[stepIndex]?.statement_line ?? null;
  }, [mode, engine, stepIndex, snapshots, vmSnapshots]);

  // Current tour caption — looks up the active snapshot's
  // `statement_line` against the tour's caption table, falling back
  // to the nearest registered earlier line so the banner stays stable
  // across follow-up steps without their own caption entry.
  const tourCaption = useMemo(() => {
    if (!tourEffective) return null;
    if (stepIndex < 0) {
      return "Press Play (or Step) to start the tour.";
    }
    const line = snapshots[stepIndex]?.statement_line ?? null;
    if (line === null) return null;
    return captionFor(tourEffective, line);
  }, [tourEffective, stepIndex, snapshots]);

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

  // (v2.27.4) Removed editor hover-range and editor cursor state —
  // they were tied to the AST tree view in Step Detail, which has
  // been replaced by the legible Structure view. The Editor still
  // accepts those props (defensive defaults of null) but the page
  // no longer sets them.

  // Bytecode pane (v2.27.10). Hidden by default. When the user
  // clicks "show bytecode" we compile the current source to a
  // chunk via the new bridge and render it below Step Detail.
  // Re-compiles on source change while the pane is open.
  const [showBytecode, setShowBytecode] = useState<boolean>(false);
  const [bytecode, setBytecode] = useState<RotChunkDump | null>(null);
  const [bytecodeError, setBytecodeError] = useState<RotError | null>(null);
  const [bytecodeLoading, setBytecodeLoading] = useState<boolean>(false);
  useEffect(() => {
    if (!showBytecode) return;
    let cancelled = false;
    setBytecodeLoading(true);
    compileToChunk(source).then((result) => {
      if (cancelled) return;
      setBytecode(result.chunk);
      setBytecodeError(result.error);
      setBytecodeLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [showBytecode, source]);

  const displayOutput = mode === "animate" ? animateOutput : pipeline.output;
  const displayError = mode === "animate" ? animateError : pipeline.error;
  const displayRunning =
    runtimeStatus.state === "loading" ||
    (mode === "run" && running) ||
    (mode === "animate" && stepping);

  // Timeline entries — projected from whichever engine is active.
  const timelineEntries: TimelineEntry[] = useMemo(() => {
    if (engine === "vm") {
      return vmSnapshots.map((s) => ({
        error: s.error,
        tooltip: `${s.op_name} @ ip ${s.prev_ip} (chunk ${s.chunk_id}, line ${s.line || "?"})`,
      }));
    }
    return snapshots.map((s) => ({
      error: s.error,
      tooltip: `${s.statement_kind} at line ${s.statement_line}:${s.statement_col}`,
    }));
  }, [engine, snapshots, vmSnapshots]);

  // Keyboard shortcuts:
  //   Cmd/Ctrl+Enter — Run (run mode) or Step (animate mode). Works
  //                    even when the editor is focused.
  //   →             — Step forward (animate mode).
  //   ←             — Step backward (animate mode).
  //   Space         — Play / Pause (animate mode).
  // Arrow + Space are gated on the editor NOT being focused so they
  // don't fight CodeMirror's own bindings.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (mode === "run") void handleRun();
        else void handleStep();
        return;
      }
      const target = e.target as HTMLElement | null;
      if (target?.closest(".cm-editor")) return;
      if (mode !== "animate") return;
      if (e.key === "ArrowRight") {
        e.preventDefault();
        void handleStep();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setPlaying(false);
        setStepIndex((i) => Math.max(0, i - 1));
      } else if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        void togglePlay();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mode, handleRun, handleStep, togglePlay]);

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
        onSelectExample={(_key, src) => {
          setSource(src);
        }}
        activeTourKey={tourEffective?.key ?? null}
        onStartTour={handleStartTour}
        mode={mode}
        onSwitchMode={switchMode}
        engine={engine}
        onEngineChange={handleEngineChange}
        running={running}
        onRun={handleRun}
        activeSnapshotCount={activeSnapshotCount}
        stepIndex={stepIndex}
        stepping={stepping}
        playing={playing}
        speedMs={speedMs}
        onSpeedChange={setSpeedMs}
        onStep={handleStep}
        onTogglePlay={togglePlay}
        onReset={handleReset}
        shareState={shareState}
        onShare={handleShare}
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
              onClear={mode === "run" ? handleClearOutput : undefined}
            />
          </div>
          {/* Run-mode stats card — only after the first Run. Animate
              mode has its own per-step instrumentation in Step Detail. */}
          {mode === "run" && pipeline.runKey > 0 && (
            <div className="flex flex-col overflow-hidden rounded-lg border bg-card">
              <RunStats
                tokens={pipeline.tokens}
                ast={pipeline.ast}
                output={pipeline.output}
                source={source}
                timings={pipeline.timings}
              />
            </div>
          )}
          {/* Tour caption banner — only when a tour is active and we
              have something to say about the current step. Lives just
              above the Step Detail card. */}
          {mode === "animate" && tourEffective && (
            <TourCaptionBanner
              tour={tourEffective}
              caption={tourCaption}
              onExit={() => setTourKey(null)}
            />
          )}
          {mode === "animate" && engine === "tree-walker" && (
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
                playing={playing}
                speedMs={speedMs}
              />
            </div>
          )}
          {mode === "animate" && engine === "vm" && (
            <div className="flex min-h-[36vh] flex-[1.8] flex-col overflow-hidden rounded-lg border border-amber-500/30 bg-card shadow-[0_0_0_1px_rgba(245,158,11,0.05)]">
              <VMStepPanel
                snapshot={
                  stepIndex >= 0 ? vmSnapshots[stepIndex] ?? null : null
                }
                previousSnapshot={
                  stepIndex > 0 ? vmSnapshots[stepIndex - 1] ?? null : null
                }
                stepIndex={stepIndex}
                totalSteps={vmSnapshots.length}
                chunkId={
                  stepIndex >= 0
                    ? vmSnapshots[stepIndex]?.chunk_id ?? "main"
                    : "main"
                }
              />
            </div>
          )}
          {/* Animate-mode bytecode pane — opt-in via the toggle in the
              card header. Compiled-on-demand from the current source. */}
          {mode === "animate" && (
            <div className="flex flex-col overflow-hidden rounded-lg border bg-card">
              <button
                type="button"
                onClick={() => setShowBytecode((v) => !v)}
                className="flex items-center justify-between gap-3 border-b border-border/60 px-3 py-2 text-xs uppercase tracking-wider text-muted-foreground hover:text-foreground"
                aria-expanded={showBytecode}
              >
                <span className="flex items-center gap-1.5">
                  Bytecode
                  {bytecodeError && (
                    <span className="rounded border border-destructive/40 bg-destructive/10 px-1 py-0.5 text-[9px] normal-case text-destructive">
                      error
                    </span>
                  )}
                </span>
                <span className="text-[10px] normal-case">
                  {showBytecode ? "hide" : "show"}
                </span>
              </button>
              {showBytecode && (
                <div className="max-h-[28vh] overflow-auto p-3">
                  {bytecodeLoading && !bytecode && (
                    <div className="text-xs text-muted-foreground">
                      Compiling...
                    </div>
                  )}
                  {bytecodeError && (
                    <pre className="whitespace-pre-wrap rounded border border-destructive/40 bg-destructive/10 p-2 font-mono text-[12px] text-destructive">
                      {bytecodeError.formatted}
                    </pre>
                  )}
                  {!bytecodeError && (
                    <BytecodeView
                      chunk={bytecode}
                      highlightLine={highlightLine}
                      empty="(no chunk yet)"
                    />
                  )}
                </div>
              )}
            </div>
          )}
          {/* Animate-mode timeline strip — only when snapshots exist.
              In Run mode there's no bottom card; the Output panel
              takes the full right column. */}
          {mode === "animate" && timelineEntries.length > 0 && (
            <div className="flex flex-col overflow-hidden rounded-lg border bg-card">
              <SnapshotTimeline
                entries={timelineEntries}
                stepIndex={stepIndex}
                onStepChange={(next) => {
                  setPlaying(false);
                  setStepIndex(next);
                }}
              />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

interface PlaygroundToolbarProps {
  runtimeStatus: RotRuntimeStatus;
  currentExample: string;
  onSelectExample: (key: string, source: string) => void;
  activeTourKey: string | null;
  onStartTour: (tour: Tour) => void;
  mode: Mode;
  onSwitchMode: (next: Mode) => void;
  engine: Engine;
  onEngineChange: (next: Engine) => void;
  running: boolean;
  onRun: () => void;
  activeSnapshotCount: number;
  stepIndex: number;
  stepping: boolean;
  playing: boolean;
  speedMs: number;
  onSpeedChange: (ms: number) => void;
  onStep: () => void;
  onTogglePlay: () => void;
  onReset: () => void;
  shareState: "idle" | "copied" | "error";
  onShare: () => void;
}

function PlaygroundToolbar(props: PlaygroundToolbarProps) {
  const {
    runtimeStatus,
    currentExample,
    onSelectExample,
    activeTourKey,
    onStartTour,
    mode,
    onSwitchMode,
    engine,
    onEngineChange,
    running,
    onRun,
    activeSnapshotCount,
    stepIndex,
    stepping,
    playing,
    speedMs,
    onSpeedChange,
    onStep,
    onTogglePlay,
    onReset,
    shareState,
    onShare,
  } = props;

  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border/60 bg-background/40 px-4 py-2 backdrop-blur">
      <div className="flex items-center gap-3">
        <span className="text-xs uppercase tracking-wider text-muted-foreground">
          Playground
        </span>
        <RuntimeBadge status={runtimeStatus} />
        <ModeToggle mode={mode} onSwitch={onSwitchMode} />
        {mode === "animate" && (
          <EngineToggle engine={engine} onSwitch={onEngineChange} />
        )}
      </div>
      <div className="flex items-center gap-2">
        <ShareButton state={shareState} onClick={onShare} />
        <TourDropdown
          activeKey={activeTourKey}
          onStartTour={onStartTour}
        />
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
            snapshotCount={activeSnapshotCount}
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

function TourDropdown({
  activeKey,
  onStartTour,
}: {
  activeKey: string | null;
  onStartTour: (tour: Tour) => void;
}) {
  return (
    <Select
      value={activeKey ?? ""}
      onValueChange={(key) => {
        const t = findTour(key);
        if (t) onStartTour(t);
      }}
    >
      <SelectTrigger
        className={cn(
          "h-8 w-[160px] gap-1.5 text-xs",
          activeKey &&
            "border-amber-500/40 text-amber-200 shadow-[0_0_0_1px_rgba(245,158,11,0.1)]",
        )}
      >
        <Compass className="h-3.5 w-3.5 opacity-80" />
        <SelectValue placeholder="Take a tour" />
      </SelectTrigger>
      <SelectContent>
        {TOURS.map((t) => (
          <SelectItem key={t.key} value={t.key} className="text-xs">
            <span className="font-medium">{t.label}</span>
            <span className="ml-2 text-muted-foreground">{t.blurb}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
}

function EngineToggle({
  engine,
  onSwitch,
}: {
  engine: Engine;
  onSwitch: (next: Engine) => void;
}) {
  return (
    <div
      className="inline-flex overflow-hidden rounded-md border border-amber-500/30"
      title="Pick the execution engine — Tree-walker steps statements, VM steps bytecode opcodes."
    >
      {(["tree-walker", "vm"] as Engine[]).map((e) => (
        <button
          key={e}
          type="button"
          onClick={() => onSwitch(e)}
          aria-pressed={engine === e}
          className={cn(
            "px-2 py-0.5 text-[10px] uppercase tracking-wider transition-colors",
            engine === e
              ? "bg-amber-500/80 text-background"
              : "bg-transparent text-muted-foreground hover:text-foreground",
          )}
        >
          {e === "tree-walker" ? "tree-walker" : "VM"}
        </button>
      ))}
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
  snapshotCount: number;
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
  snapshotCount,
  stepIndex,
  stepping,
  playing,
  speedMs,
  onSpeedChange,
  onStep,
  onTogglePlay,
  onReset,
}: AnimateControlsProps) {
  const hasSnapshots = snapshotCount > 0;
  const atEnd = hasSnapshots && stepIndex >= snapshotCount - 1;
  // Step counter: "0 / 0" before first step; "N / total" after.
  const counter = hasSnapshots
    ? `${Math.max(stepIndex + 1, 1)} / ${snapshotCount}`
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
        title="Reset to before first step (use ← to step back one)"
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
        title="Advance one statement (⌘↵ or →)"
      >
        {stepping ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <SkipForward className="h-3.5 w-3.5" />
        )}
        Step
        <span className="ml-1 hidden text-[10px] opacity-70 sm:inline">
          →
        </span>
      </Button>
      <Button
        size="sm"
        onClick={onTogglePlay}
        disabled={stepping}
        className="gap-1.5"
        title={playing ? "Pause auto-step (space)" : "Auto-step to end (space)"}
      >
        {playing ? (
          <Pause className="h-3.5 w-3.5" />
        ) : (
          <Play className="h-3.5 w-3.5" />
        )}
        {playing ? "Pause" : "Play"}
        <span className="ml-1 hidden text-[10px] opacity-70 sm:inline">
          ␣
        </span>
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

function TourCaptionBanner({
  tour,
  caption,
  onExit,
}: {
  tour: Tour;
  caption: string | null;
  onExit: () => void;
}) {
  return (
    <div className="flex flex-col overflow-hidden rounded-lg border border-amber-500/30 bg-amber-500/5">
      <div className="flex items-center justify-between border-b border-amber-500/20 px-3 py-1.5">
        <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-amber-300">
          <Compass className="h-3 w-3" />
          <span>Tour</span>
          <span className="text-muted-foreground">·</span>
          <span className="normal-case text-amber-200/90">{tour.label}</span>
        </div>
        <button
          type="button"
          onClick={onExit}
          className="text-[10px] uppercase tracking-wider text-muted-foreground hover:text-foreground"
          title="Exit tour (keeps source loaded)"
        >
          exit
        </button>
      </div>
      <div className="min-h-[2rem] px-3 py-2 text-[12.5px] leading-relaxed text-foreground/90">
        <AnimatePresence mode="wait">
          {caption ? (
            <motion.div
              key={caption}
              initial={{ opacity: 0, y: 3 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -3 }}
              transition={{ duration: 0.2 }}
            >
              {caption}
            </motion.div>
          ) : (
            <motion.div
              key="empty"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="text-muted-foreground"
            >
              {tour.blurb}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

function ShareButton({
  state,
  onClick,
}: {
  state: "idle" | "copied" | "error";
  onClick: () => void;
}) {
  const copied = state === "copied";
  const errored = state === "error";
  return (
    <Button
      size="sm"
      variant="outline"
      onClick={onClick}
      className={cn(
        "gap-1.5 transition-colors",
        copied && "border-emerald-500/50 text-emerald-300",
        errored && "border-destructive/50 text-destructive",
      )}
      title="Copy a shareable URL with the current source encoded in the query string"
    >
      {copied ? (
        <Check className="h-3.5 w-3.5" />
      ) : (
        <Link2 className="h-3.5 w-3.5" />
      )}
      <span className="hidden sm:inline">
        {copied ? "Copied" : errored ? "Error" : "Share"}
      </span>
    </Button>
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

