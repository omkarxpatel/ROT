// Pyodide runtime loader for the ROT playground.
//
// Lifecycle:
//   1. `loadRotRuntime()` is called on the first "Run" click.
//   2. It injects the Pyodide loader script from the CDN, calls
//      `loadPyodide()`, fetches the rot/*.py sources from /rot_package/,
//      writes them into Pyodide's virtual filesystem under /rot/, and
//      defines a Python function `rot_compile_and_run(source)` that
//      returns a JSON-serializable dict.
//   3. Subsequent calls re-use the cached runtime.
//
// The runtime is intentionally a singleton — Pyodide is ~10MB to load
// and re-initializing per Run would defeat the cache.
//
// All errors are caught and surfaced via the return shape so the UI
// never sees a raw exception.

import { ROT_VERSION } from "@/lib/rot-version";

const PYODIDE_VERSION = "0.27.0";
const PYODIDE_CDN = `https://cdn.jsdelivr.net/pyodide/v${PYODIDE_VERSION}/full`;

export interface RotToken {
  lexeme: string;
  kind: string;
  line: number;
  col: number;
}

// AST nodes from `dataclasses.asdict` look like
//   { __type__: "FuncDef", name: "...", params: [...], body: { __type__: "Block", ... }, line, col }
// Recursive — children are AstNode | AstNode[] | primitives.
export type AstValue =
  | string
  | number
  | boolean
  | null
  | AstNode
  | AstValue[];

export interface AstNode {
  __type__: string;
  [key: string]: AstValue;
}

export interface RotError {
  message: string;
  line: number;
  col: number;
  formatted: string; // rustc-style block
  stage: "lex" | "parse" | "interpret" | "internal";
}

export interface RotRunResult {
  tokens: RotToken[];
  ast: AstNode | null;
  output: string;
  error: RotError | null;
  timings: {
    lexMs: number;
    parseMs: number;
    interpretMs: number;
  };
}

// --- Step-mode (v2.26.x — Milestone 1) ---

export interface RotEnvFrame {
  scope_kind: string;
  scope_label: string;
  // Values are rendered via ROT's _stringify on the Python side so the
  // UI only ever has to display strings (null, true/false, list/dict
  // ROT-syntax, <function foo>, <instance of X>, etc.).
  bindings: Record<string, string>;
}

export interface RotSnapshot {
  statement_line: number;
  statement_col: number;
  statement_kind: string;
  env: RotEnvFrame[];
  output_since_last: string;
  error: string | null;
  // Loop context (v2.26.21). `loop_iter` is the 1-indexed iteration
  // this snapshot belongs to, or null if not inside a loop body.
  // `loop_total` is the iterable's length for `for` loops, null for
  // `while` loops where the count isn't known ahead of time.
  loop_iter: number | null;
  loop_total: number | null;
}

export interface RotStepResult {
  tokens: RotToken[];
  ast: AstNode | null;
  snapshots: RotSnapshot[];
  // Only set for lex/parse failures or interpreter bugs — user-level
  // runtime errors land in the final snapshot's `error` field instead.
  error: RotError | null;
  timings: {
    lexMs: number;
    parseMs: number;
    interpretMs: number;
  };
}

// --- Bytecode (v2.27.10) ---

export type RotBytecodeArg = number | string | boolean | null;

export type RotInstr = [string, ...RotBytecodeArg[]];

export interface RotChunkDump {
  code: RotInstr[];
  constants: RotConstant[];
  names: string[];
}

export type RotConstant =
  | string
  | number
  | boolean
  | null
  | RotFunctionDump;

export interface RotFunctionDump {
  __type__: "RotFunctionValue";
  name: string;
  params: string[];
  chunk: RotChunkDump | null;
}

export interface RotCompileResult {
  chunk: RotChunkDump | null;
  error: RotError | null;
  timings: { lexMs: number; parseMs: number; compileMs: number };
}

export interface RotRuntimeStatus {
  state: "idle" | "loading" | "ready" | "error";
  message?: string;
}

// Minimal subset of the Pyodide JS API we use. We don't depend on the
// upstream types package so the Next.js build doesn't need to resolve a
// .d.ts module that doesn't exist at the version we pin to.
interface PyProxy {
  toJs: (opts?: { dict_converter?: (entries: Iterable<[unknown, unknown]>) => unknown }) => unknown;
  destroy: () => void;
}

interface PyodideInterface {
  FS: {
    mkdirTree: (path: string) => void;
    writeFile: (path: string, data: string | Uint8Array, opts?: { encoding?: string }) => void;
  };
  runPython: (code: string) => unknown;
  runPythonAsync: (code: string) => Promise<unknown>;
  globals: {
    get: (name: string) => unknown;
    set: (name: string, value: unknown) => void;
  };
}

interface PyodideLoader {
  loadPyodide: (opts: { indexURL: string }) => Promise<PyodideInterface>;
}

// Declare the global injected by the Pyodide loader script.
declare global {
  interface Window {
    loadPyodide?: PyodideLoader["loadPyodide"];
  }
}

// Singleton state.
let runtimePromise: Promise<PyodideInterface> | null = null;
let runtimeStatus: RotRuntimeStatus = { state: "idle" };
const statusListeners = new Set<(s: RotRuntimeStatus) => void>();

function setStatus(s: RotRuntimeStatus) {
  runtimeStatus = s;
  for (const l of statusListeners) l(s);
}

export function getRuntimeStatus(): RotRuntimeStatus {
  return runtimeStatus;
}

export function onRuntimeStatus(
  cb: (s: RotRuntimeStatus) => void,
): () => void {
  statusListeners.add(cb);
  return () => statusListeners.delete(cb);
}

function injectScript(src: string): Promise<void> {
  // If already present, resolve immediately.
  if (typeof document === "undefined") {
    return Promise.reject(new Error("not in a browser environment"));
  }
  const existing = document.querySelector<HTMLScriptElement>(
    `script[src="${src}"]`,
  );
  if (existing && window.loadPyodide) {
    return Promise.resolve();
  }
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error(`failed to load ${src}`));
    document.head.appendChild(s);
  });
}

// All asset fetches go through `versioned(url)` so changing `ROT_VERSION`
// implicitly busts the cache. Without this, a `cache: "force-cache"`
// browser entry would happily serve stale `rot/*.py` files forever —
// notably keeping a pre-v2.26 `interpreter.py` (no `iter_execute`)
// glued to a v2.26+ bridge that calls `iter_execute`, breaking step
// mode without any visible signal.
function versioned(url: string): string {
  const sep = url.includes("?") ? "&" : "?";
  return `${url}${sep}v=${encodeURIComponent(ROT_VERSION)}`;
}

async function fetchText(url: string): Promise<string> {
  // `cache: "default"` lets the browser respect ETag / Last-Modified
  // round-trips. Combined with the versioned URL this gives us "cache
  // hard while the version is stable, refetch instantly on version
  // bump" — the right behavior for a static site whose files only
  // change between releases.
  const r = await fetch(versioned(url), { cache: "default" });
  if (!r.ok) {
    throw new Error(`fetch ${url} failed: ${r.status} ${r.statusText}`);
  }
  return r.text();
}

async function fetchJson<T>(url: string): Promise<T> {
  const r = await fetch(versioned(url), { cache: "default" });
  if (!r.ok) {
    throw new Error(`fetch ${url} failed: ${r.status} ${r.statusText}`);
  }
  return r.json() as Promise<T>;
}

// Python glue. Defines `rot_compile_and_run(source)` once on startup;
// subsequent calls just invoke it.
const ROT_BRIDGE_PY = `
import sys, io, contextlib, time, dataclasses
import json as _json

# Import the rot package we just wrote to the virtual filesystem.
# /rot is on sys.path via Pyodide's default cwd; add explicitly to be safe.
if "/" not in sys.path:
    sys.path.insert(0, "/")

from rot.lexer import Lexer
from rot.syntax import Parser
from rot.interpreter import Interpreter
from rot.errors import RotError, LexerError, ParserError, InterpreterError


def _ast_to_dict(node):
    """Recursive dataclass -> plain-dict serialization, tagged with
    the node's class name under __type__ so the UI can render a typed
    tree."""
    if dataclasses.is_dataclass(node) and not isinstance(node, type):
        out = {"__type__": type(node).__name__}
        for f in dataclasses.fields(node):
            out[f.name] = _ast_to_dict(getattr(node, f.name))
        return out
    if isinstance(node, list):
        return [_ast_to_dict(x) for x in node]
    if isinstance(node, tuple):
        return [_ast_to_dict(x) for x in node]
    # Primitives (str, int, float, bool, None) pass through.
    return node


def _stage_from_exc(exc):
    if isinstance(exc, LexerError):
        return "lex"
    if isinstance(exc, ParserError):
        return "parse"
    if isinstance(exc, InterpreterError):
        return "interpret"
    return "internal"


def _error_dict(exc, source):
    return {
        "message": getattr(exc, "message", str(exc)),
        "line": int(getattr(exc, "line", 0) or 0),
        "col": int(getattr(exc, "col", 0) or 0),
        "formatted": exc.format(source, "<playground>") if isinstance(exc, RotError) else f"error: {exc}",
        "stage": _stage_from_exc(exc),
    }


def rot_compile_to_chunk(source):
    """Lex / parse / compile \`source\` to bytecode. Returns a JSON
    string with:
        - chunk:   {code, constants, names} or null on failure
        - error:   null or {message, line, col, formatted, stage}
        - timings: {lexMs, parseMs, compileMs}
    """
    from rot.codegen import Compiler as _Compiler
    result = {
        "chunk": None,
        "error": None,
        "timings": {"lexMs": 0.0, "parseMs": 0.0, "compileMs": 0.0},
    }
    t0 = time.perf_counter()
    try:
        tokens = Lexer().tokenize(source)
    except Exception as e:
        result["timings"]["lexMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["lexMs"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    try:
        program = Parser(tokens).parse()
    except Exception as e:
        result["timings"]["parseMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["parseMs"] = (time.perf_counter() - t0) * 1000
    t0 = time.perf_counter()
    try:
        chunk = _Compiler().compile(program)
    except NotImplementedError as e:
        result["timings"]["compileMs"] = (time.perf_counter() - t0) * 1000
        # Codegen doesn't cover every statement type yet; surface the
        # gap as an "interpret"-stage error so the UI can show it.
        result["error"] = {
            "message": str(e),
            "line": 0,
            "col": 0,
            "formatted": f"codegen: {e}",
            "stage": "interpret",
        }
        return _json.dumps(result)
    except Exception as e:
        result["timings"]["compileMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["compileMs"] = (time.perf_counter() - t0) * 1000
    result["chunk"] = chunk.to_dict()
    return _json.dumps(result)


def rot_step(source):
    """Lex / parse / step-execute \`source\`. Returns a JSON string with:
        - tokens:    list of {lexeme, kind, line, col}
        - ast:       a typed tree (or null on lex/parse failure)
        - snapshots: list of Snapshot.to_dict() — one per top-level
                     statement; the last entry may carry \`error\`.
        - error:     null EXCEPT on lex/parse failures or interpreter
                     bugs. User-level runtime errors surface as
                     \`snapshots[-1].error\`, not here.
        - timings:   {lexMs, parseMs, interpretMs}
    """
    result = {
        "tokens": [],
        "ast": None,
        "snapshots": [],
        "error": None,
        "timings": {"lexMs": 0.0, "parseMs": 0.0, "interpretMs": 0.0},
    }
    # --- lex ---
    t0 = time.perf_counter()
    try:
        tokens = Lexer().tokenize(source)
    except Exception as e:
        result["timings"]["lexMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["lexMs"] = (time.perf_counter() - t0) * 1000
    result["tokens"] = [
        {"lexeme": t.lexeme, "kind": t.kind, "line": t.line, "col": t.col}
        for t in tokens
    ]
    # --- parse ---
    t0 = time.perf_counter()
    try:
        program = Parser(tokens).parse()
    except Exception as e:
        result["timings"]["parseMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["parseMs"] = (time.perf_counter() - t0) * 1000
    try:
        result["ast"] = _ast_to_dict(program)
    except Exception:
        result["ast"] = None
    # --- step-mode interpret ---
    # iter_execute is designed not to raise for user errors (those
    # become snapshot.error). Wrapping in try/except catches genuine
    # interpreter bugs so they reach the UI cleanly.
    t0 = time.perf_counter()
    try:
        interp = Interpreter()
        for snap in interp.iter_execute(program):
            result["snapshots"].append(snap.to_dict())
    except Exception as e:
        result["timings"]["interpretMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["interpretMs"] = (time.perf_counter() - t0) * 1000
    return _json.dumps(result)


def rot_compile_and_run(source):
    """Lex / parse / interpret \`source\`. Returns a JSON string with:
        - tokens: list of {lexeme, kind, line, col}
        - ast:    a typed tree (or null on lex/parse failure)
        - output: captured stdout
        - error:  null or {message, line, col, formatted, stage}
        - timings: {lexMs, parseMs, interpretMs}
    """
    result = {
        "tokens": [],
        "ast": None,
        "output": "",
        "error": None,
        "timings": {"lexMs": 0.0, "parseMs": 0.0, "interpretMs": 0.0},
    }
    # --- lex ---
    t0 = time.perf_counter()
    try:
        tokens = Lexer().tokenize(source)
    except Exception as e:
        result["timings"]["lexMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["lexMs"] = (time.perf_counter() - t0) * 1000
    result["tokens"] = [
        {"lexeme": t.lexeme, "kind": t.kind, "line": t.line, "col": t.col}
        for t in tokens
    ]
    # --- parse ---
    t0 = time.perf_counter()
    try:
        program = Parser(tokens).parse()
    except Exception as e:
        result["timings"]["parseMs"] = (time.perf_counter() - t0) * 1000
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["parseMs"] = (time.perf_counter() - t0) * 1000
    try:
        result["ast"] = _ast_to_dict(program)
    except Exception as e:
        # If serialization fails (shouldn't, but defensive), keep going
        # and report the error in the trace slot.
        result["ast"] = None
        result["error"] = {
            "message": f"ast serialization failed: {e}",
            "line": 0,
            "col": 0,
            "formatted": f"error: ast serialization failed: {e}",
            "stage": "internal",
        }
    # --- interpret ---
    t0 = time.perf_counter()
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            Interpreter().execute(program)
    except Exception as e:
        result["timings"]["interpretMs"] = (time.perf_counter() - t0) * 1000
        result["output"] = buf.getvalue()
        result["error"] = _error_dict(e, source)
        return _json.dumps(result)
    result["timings"]["interpretMs"] = (time.perf_counter() - t0) * 1000
    result["output"] = buf.getvalue()
    return _json.dumps(result)
`;

async function initRuntime(): Promise<PyodideInterface> {
  if (typeof window === "undefined") {
    throw new Error("pyodide can only run in the browser");
  }
  setStatus({ state: "loading", message: "fetching pyodide..." });
  await injectScript(`${PYODIDE_CDN}/pyodide.js`);
  if (!window.loadPyodide) {
    throw new Error("pyodide loader missing after script load");
  }
  const pyodide = await window.loadPyodide({ indexURL: PYODIDE_CDN });

  setStatus({ state: "loading", message: "loading rot..." });
  // Fetch the manifest of rot/*.py we copied at build time.
  const manifest = await fetchJson<{ files: string[] }>(
    "/rot_package/manifest.json",
  );
  pyodide.FS.mkdirTree("/rot");
  // Fetch every .py in parallel and write into /rot/.
  await Promise.all(
    manifest.files.map(async (name) => {
      const text = await fetchText(`/rot_package/${name}`);
      pyodide.FS.writeFile(`/rot/${name}`, text, { encoding: "utf8" });
    }),
  );

  // Strip the colorama import from compiler.py — Pyodide doesn't have
  // colorama by default and `trace=False` is all we use anyway.
  // Easier than `micropip.install("colorama")` which adds ~100ms.
  pyodide.runPython(`
import sys
# Provide a stub colorama so \`from colorama import Fore, init\` succeeds.
import types as _types
_mod = _types.ModuleType("colorama")
class _Fore:
    RED = ""
    RESET = ""
def _init(*a, **kw):
    return None
_mod.Fore = _Fore
_mod.init = _init
sys.modules["colorama"] = _mod
`);

  // Install the bridge.
  pyodide.runPython(ROT_BRIDGE_PY);

  setStatus({ state: "ready" });
  return pyodide;
}

export function loadRotRuntime(): Promise<PyodideInterface> {
  if (!runtimePromise) {
    runtimePromise = initRuntime().catch((err) => {
      setStatus({
        state: "error",
        message: err instanceof Error ? err.message : String(err),
      });
      // Reset so a retry can be attempted.
      runtimePromise = null;
      throw err;
    });
  }
  return runtimePromise;
}

const EMPTY_RESULT: RotRunResult = {
  tokens: [],
  ast: null,
  output: "",
  error: null,
  timings: { lexMs: 0, parseMs: 0, interpretMs: 0 },
};

export async function compileAndRun(source: string): Promise<RotRunResult> {
  let pyodide: PyodideInterface;
  try {
    pyodide = await loadRotRuntime();
  } catch (e) {
    return {
      ...EMPTY_RESULT,
      error: {
        message: e instanceof Error ? e.message : String(e),
        line: 0,
        col: 0,
        formatted: `error: ${e instanceof Error ? e.message : String(e)}`,
        stage: "internal",
      },
    };
  }
  // Pass the source via globals to avoid string-escaping headaches.
  pyodide.globals.set("__rot_source__", source);
  const jsonStr = pyodide.runPython(
    `rot_compile_and_run(__rot_source__)`,
  ) as string;
  try {
    return JSON.parse(jsonStr) as RotRunResult;
  } catch (e) {
    return {
      ...EMPTY_RESULT,
      error: {
        message: `json decode failed: ${e instanceof Error ? e.message : String(e)}`,
        line: 0,
        col: 0,
        formatted: `error: json decode failed`,
        stage: "internal",
      },
    };
  }
}

const EMPTY_STEP_RESULT: RotStepResult = {
  tokens: [],
  ast: null,
  snapshots: [],
  error: null,
  timings: { lexMs: 0, parseMs: 0, interpretMs: 0 },
};

export async function compileAndStep(source: string): Promise<RotStepResult> {
  let pyodide: PyodideInterface;
  try {
    pyodide = await loadRotRuntime();
  } catch (e) {
    return {
      ...EMPTY_STEP_RESULT,
      error: {
        message: e instanceof Error ? e.message : String(e),
        line: 0,
        col: 0,
        formatted: `error: ${e instanceof Error ? e.message : String(e)}`,
        stage: "internal",
      },
    };
  }
  pyodide.globals.set("__rot_source__", source);
  const jsonStr = pyodide.runPython(`rot_step(__rot_source__)`) as string;
  try {
    return JSON.parse(jsonStr) as RotStepResult;
  } catch (e) {
    return {
      ...EMPTY_STEP_RESULT,
      error: {
        message: `json decode failed: ${e instanceof Error ? e.message : String(e)}`,
        line: 0,
        col: 0,
        formatted: `error: json decode failed`,
        stage: "internal",
      },
    };
  }
}

const EMPTY_COMPILE_RESULT: RotCompileResult = {
  chunk: null,
  error: null,
  timings: { lexMs: 0, parseMs: 0, compileMs: 0 },
};

export async function compileToChunk(
  source: string,
): Promise<RotCompileResult> {
  let pyodide: PyodideInterface;
  try {
    pyodide = await loadRotRuntime();
  } catch (e) {
    return {
      ...EMPTY_COMPILE_RESULT,
      error: {
        message: e instanceof Error ? e.message : String(e),
        line: 0,
        col: 0,
        formatted: `error: ${e instanceof Error ? e.message : String(e)}`,
        stage: "internal",
      },
    };
  }
  pyodide.globals.set("__rot_source__", source);
  const jsonStr = pyodide.runPython(
    `rot_compile_to_chunk(__rot_source__)`,
  ) as string;
  try {
    return JSON.parse(jsonStr) as RotCompileResult;
  } catch (e) {
    return {
      ...EMPTY_COMPILE_RESULT,
      error: {
        message: `json decode failed: ${e instanceof Error ? e.message : String(e)}`,
        line: 0,
        col: 0,
        formatted: `error: json decode failed`,
        stage: "internal",
      },
    };
  }
}

export { ROT_VERSION };
