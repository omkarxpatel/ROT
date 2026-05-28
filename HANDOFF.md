# HANDOFF — Session context for ROT

A snapshot of project state, conventions, and the next strategic direction for a new Claude session picking up where the last one left off. Self-sufficient by design — read this and you have everything you need. For deeper context, see [`README.md`](README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`CHANGELOG.md`](CHANGELOG.md) (newest first), [`BUG_REPORT.md`](BUG_REPORT.md) (the v2.13.0 audit), and [`paper/main.pdf`](paper/main.pdf) (the design retrospective).

## TL;DR

ROT is at **v2.27.17**, **807 tests passing**, all CI green.

- **Milestone 1 shipped** (v2.26.0–.29 + polish): generator-based step-mode interpreter, fully redesigned playground with three phases (Read · Parse · Run), localStorage persistence, share-by-URL, snapshot timeline, error-as-snapshot, deep stepping into function bodies / loops / branches, keyboard navigation, pause-on-error.
- **Milestone 2 is well underway** (v2.27.0–.17): bytecode opcode set + Chunk + Compiler + stack VM. Covers literals, variables, arithmetic, comparisons, logical short-circuit, if/elif/else, while loops, for loops, break/continue, lists/dicts/indexing, function calls with frame stack, classes with `init`/methods/`this`, compound assigns, try/catch/throw. `python -m rot --vm file.rot` runs `examples/fizzbuzz.rot` and `examples/counter.rot` end-to-end through the bytecode path. The Bytecode pane in the playground (opt-in) shows the compiled chunk with per-statement instruction highlighting that follows the active snapshot.

**Where to pick up.** Several natural directions, in order of likely impact — see [§ Where to go next](#where-to-go-next) for the ranked list.

---

## What changed since the last handoff (v2.25.17 → v2.27.17)

### Milestone 1 (v2.26.0–.29) — step-mode interpreter + playground redesign

Foundation work (v2.26.0–.4 — interpreter backend):

- [`rot/interpreter.py`](rot/interpreter.py) gained `Snapshot` and `EnvFrame` dataclasses and `iter_execute(program) -> Iterator[Snapshot]`. The fast `execute()` path is unchanged (`_step_mode=False`).
- `Environment._env_snapshot()` walks the scope chain and returns frames outermost-first. The 5 construction sites are labeled (`builtins`, `global`, `function`, `method`, `catch`).
- `cout` / `coutln` route through a per-interpreter `_capture_buffer` when step mode is engaged. Each snapshot carries its statement's output.
- Errors become `Snapshot.error` instead of raises; iteration halts after the failing statement.
- Pyodide bridge exposes `rot_step(source)` returning JSON-safe snapshots via `Snapshot.to_dict()` / `EnvFrame.to_dict()`.

Playground UI (v2.26.5–.8):

- `Animate` mode added. Toolbar exposes Step / Play (with pause) / Reset / a speed slider (50ms–2000ms).
- A dedicated `StepPanel` in the right column. Animations are loud (per user request): per-binding slot-machine values, line-pulse decoration in the editor on each step, dive-in / dive-out for function-call frames.
- Call breadcrumb (`global › funct greet`), loop-iter badge, ✓ done pill / halted pill at end.

Polish line (v2.26.9–.29):

- Cache-bust hotfix for the Pyodide bridge (URLs now carry `?v=${ROT_VERSION}`).
- Source-line preview colored per-token; token chips fall from above into place; AST-leaf reveals trigger a pulse on the matching token chip.
- AST node → env binding pulse when a new/changed binding appears (closes the parse → execute visual chain).
- Editor gets ROT-specific syntax highlighting matching the same chip palette.
- Iteration counter for loops via `Snapshot.loop_iter` / `loop_total`.
- Output panel streams new text one char at a time with an emerald-fading flash.
- Deep stepping: snapshots fire for every statement that runs, including inside function bodies, loops, branches.
- Keyboard shortcuts: `→` step forward, `←` step backward, `Space` Play/Pause, `Cmd/Ctrl+Enter` Run/Step.

### M1 finish — Step Detail redesign (v2.27.4 → .6)

After feedback that the four-stage Step Detail was clutter, the panel was redesigned:

- **Three phases now: Read · Parse · Run.** No Tokens chip strip, no dense AST tree.
- The Parse stage uses a new `StructureView` component that pretty-prints the AST as colored, indented source-like code — handles every statement (`Assign`, `LetStmt`, `IfStmt`, `WhileStmt`, `ForStmt`, `FuncDef`, `ClassDef`, `TryCatch`, `IndexAssign`, `MemberAssign`, …) and every expression (`BinaryOp`, `Call`, `MemberAccess`, `Index`, `ListLit`, `DictLit`, …).
- Run mode dropped the Pipeline panel entirely. Right column is just Output. AST tree and Tokens accordion items were deleted; `pipeline-panel.tsx` and `ast-view.tsx` are gone.
- localStorage persistence (the editor's source survives refresh).
- Share-by-URL: a Share button copies a `?src=<base64>` link.

### Milestone 2 — bytecode VM (v2.27.0–.14)

Three new files in `rot/`:

```
rot/opcodes.py    Op(IntEnum) — ~35 opcodes
rot/codegen.py    Chunk + Compiler + RotFunctionValue / RotClassValue /
                  RotInstanceValue / RotBoundMethod runtime types
rot/vm.py         stack-based VM with frame stack, handler stack,
                  globals dict, dispatch loop
tests/test_codegen.py   ~30 tests
tests/test_vm.py        ~50 tests
```

Opcode set shipped:

- **Stack:** `LOAD_CONST`, `LOAD_NULL`, `LOAD_TRUE`, `LOAD_FALSE`, `POP`, `DUP`
- **Variables:** `LOAD_NAME`, `STORE_NAME`
- **Arithmetic:** `ADD`, `SUB`, `MUL`, `DIV`, `MOD`, `NEG`
- **Comparison:** `EQ`, `NE`, `LT`, `LE`, `GT`, `GE`
- **Boolean:** `NOT`
- **Control flow:** `JUMP`, `JUMP_IF_FALSE`, `JUMP_IF_TRUE`
- **Iteration:** `GET_ITER`, `ITER_NEXT`
- **Collections:** `BUILD_LIST`, `BUILD_DICT`, `GET_INDEX`, `SET_INDEX`
- **Members:** `GET_MEMBER`, `SET_MEMBER`
- **Exceptions:** `BEGIN_TRY`, `END_TRY`, `RAISE`
- **Function calls:** `CALL`, `RETURN_VALUE`
- **Halt:** `RETURN`

`Compiler` covers everything the VM has opcodes for, plus compound assigns (`x += 1`, `this.x += 1`). CLI `python -m rot --vm <file>` is wired and verified against `examples/fizzbuzz.rot` and `examples/counter.rot`.

The Pyodide bridge exposes `rot_compile_to_chunk(source)` → JSON dump with per-instruction source-line attribution (`Chunk.lines` parallel to `Chunk.code`). The playground has an opt-in **Bytecode** card under Step Detail (Animate mode only) showing the compiled chunk with the matching-line instructions amber-highlighted, others dimmed.

---

## Project layout

```
rot/                  the language package (~5,000 LOC after M2)
├── __init__.py       __version__ = "2.27.17"
├── __main__.py       `python -m rot` entry
├── cli.py            argparse CLI; supports `--vm`, `--trace`, `--no-run`, `--repl`
├── compiler.py       orchestrates lex → parse → interpret (tree-walker path)
├── lexer.py          hand-rolled char-by-char tokenizer
├── token.py          Token dataclass (lexeme, kind, line, col)
├── keywords.py       KEYWORDS dict
├── ast.py            AST node dataclasses; every node carries line/col
├── syntax.py         recursive-descent parser; Pratt for expressions
├── interpreter.py    tree-walking interpreter (reference engine)
├── builtins.py       standard library (35+ builtins)
├── repl.py           interactive REPL with multi-line + persistent history
├── errors.py         RotError + rustc-style rendering
├── opcodes.py        Op(IntEnum) for the bytecode VM           [NEW M2]
├── codegen.py        AST → bytecode Compiler + Chunk + value types  [NEW M2]
└── vm.py             stack-based bytecode VM                   [NEW M2]
tests/                807 tests total
├── test_*.py         per-layer tests (lexer, syntax, interpreter, ...)
├── test_codegen.py   M2 codegen tests                          [NEW]
└── test_vm.py        M2 VM tests                               [NEW]
examples/             7 .rot programs with .expected golden outputs
paper/                10-page LaTeX design retrospective (main.pdf included)
web/                  Next.js 15 + Pyodide site: landing / docs / playground / paper PDF
  src/
    app/playground/page.tsx                — the playground entry point
    components/
      editor.tsx               CodeMirror w/ syntax-highlight + line-highlight
      output-panel.tsx         Output panel with type-on streaming
      step-panel.tsx           the 3-phase Read·Parse·Run card (animate mode)
      structure-view.tsx       pretty-printed AST in the Parse stage
      env-view.tsx             env diff w/ slot-machine values
      bytecode-view.tsx        opt-in Bytecode pane
      snapshot-timeline.tsx    scrubbable strip of step dots
      tokens-view.tsx          re-exports tokenTextColor helper
    lib/
      pyodide-runtime.ts       bridge: compileAndRun / compileAndStep / compileToChunk
ARCHITECTURE.md       deep design doc (somewhat stale on M2)
CHANGELOG.md          per-release notes (newest first)
BUG_REPORT.md         v2.13.0 audit
HANDOFF.md            this file
```

---

## What `python -m rot --vm` covers (M2 surface)

```rot
// All of this works via the VM:

x = 1
y = 2 + 3
s = "hi " + x
b = (1 < 2) and not false

if (x > 0) { coutln(x) }
elseif (x == 0) { coutln("zero") }
else { coutln("negative") }

while (x < 5) {
    if (x == 3) { break }
    x += 1
}

for n in [10 | 20 | 30] {
    cout(n)
}

funct fac(n) {
    if (n <= 1) { return 1 }
    return n * fac(n - 1)
}
coutln(fac(5))           // 120

class Counter {
    init(start) { this.n = start }
    tick() { this.n += 1 }
}
c = Counter(10)
c.tick()
coutln(c.n)              // 11

try {
    throw "boom"
} catch (e) {
    coutln("caught: " + e)
}
```

What `--vm` does **not** yet cover:

- **`Slice`** expressions (`xs[1:3]`) — codegen raises `NotImplementedError`.
- **`Import`** statements — codegen raises.
- **`finally` block** on `try` — codegen raises.
- **Closures** — a function's free names resolve to globals only; there's no upvalue mechanism for capturing enclosing-function locals.
- **`super`** — same status as the tree-walker (reserved, errors).
- **Compound `IndexAssign`** (`xs[i] += 1`) — needs a `DUP_TOP_TWO` opcode.

The tree-walker covers all of these — `python -m rot file.rot` (no `--vm`) is the default and handles them.

---

## Current playground layout

After the cleanup pass:

**Run mode (default):**

- Left: editor (source + line numbers + ROT syntax-highlight, persists to localStorage).
- Right: Output panel, full height. No Pipeline. Press Run → output appears.

**Animate mode:**

- Left: editor (with the amber-pulsing current-line decoration).
- Right column:
  - Output panel (top, smaller). Streams text per `cout`/`coutln`.
  - **Step Detail** card (middle, biggest). Three phases per snapshot:
    - **Read** — the source line, colored per-token, click any token to jump the editor cursor.
    - **Parse** — pretty-printed code via `StructureView`, with a small label header naming the statement kind ("Assignment", "Function call", "Conditional", …).
    - **Run** — explainer + env diff (slot-machine values, emerald/amber dots), printed-output block.
  - **Bytecode** card (optional, toggleable). Shows the compiled chunk with instructions highlighted on the active snapshot's source line.
  - Snapshot Timeline (bottom). Click any dot to jump.

Toolbar carries: mode toggle (Run / Animate), Share button, examples dropdown, Run or Step / Play / Pause / Reset / Speed slider.

Keyboard: `→` / `←` step, `Space` play/pause, `Cmd-Enter` run-or-step.

---

## Recent UX hotfixes (v2.27.15–.17)

- **v2.27.15:** removed `BindingRow.scrollIntoView` + replaced `SnapshotTimeline`'s `scrollIntoView` with `container.scrollTo({left})`. Both were dragging the Step Detail panel during Play.
- **v2.27.16:** fixed hydration mismatch when loading a `?src=…` shared link. The lazy `useState(readInitialSource)` initializer was returning fizzbuzz on the server and the URL-decoded source on the client. Moved the URL/localStorage check to a `useEffect`.
- **v2.27.17:** Step Detail now scrolls its viewport back to the top on every step change. Without this, a user who scrolled down to peek at Run would never see Read / Parse on the next snapshot.

---

## Open issues / known gaps

- **"Precode does not show the fizzbuzz that automatically shows in source."** The user reported this near the end of the session, just before asking for this handoff. Unclear which element they meant by "precode" — best guess is the Step Detail panel's Source/Parse preview before the first Step has been taken (currently shows the `OnboardingMessage`, not the source). Worth clarifying with the user; if confirmed, the fix is to render a preview of the program's source (or the first statement's pretty-printed form) before any snapshot exists. See [`web/src/components/step-panel.tsx`](web/src/components/step-panel.tsx) — `OnboardingMessage` is the function to either replace or extend.
- **VM step mode is not yet exposed in the playground.** The Bytecode pane is static-per-source — opcodes don't animate as the VM executes. The tree-walker still drives Step Detail. Wiring `rot_step_vm(source)` (opcode-level snapshots, with IP marker + stack visualization) is the original "watch the stack machine execute opcode-by-opcode" promise from HANDOFF and is the natural next big lift.
- **VM `finally`, `Slice`, `Import`, closures** — all raise `NotImplementedError` at codegen time. Tree-walker handles them. The `try { ... } finally { ... }` correctness under uncaught propagation / return / break / continue is what blocks finally — needs proper exception-flow handling.
- **VM doesn't freeze builtins.** A user program can `cout = 5` and clobber the builtin (the tree-walker rejects this). Probably ship a frozen-globals layer when polishing M2.
- **`compileToChunk` doesn't carry trace timings to the UI yet** — only `compileAndRun` and `compileAndStep` do. The Bytecode pane shows a "Compiling..." indicator but no timings.
- **Hover / click-through cross-linking** between StructureView and the editor / Bytecode pane is gone (was on the AST tree before v2.27.4's redesign). Could be added back targeting the new StructureView lines if pedagogically valuable.

---

## Where to go next

Ranked by likely impact for a new session, picking up at v2.27.17:

### 1. VM step mode in the playground (M2's headline)

The bytecode VM works end-to-end via the CLI. The playground exposes the *static* chunk. The next big win is to add opcode-level animation to the playground:

- Add `Interpreter`-equivalent step mode to `VM` — yield a snapshot after each opcode (similar to `Snapshot` but with `chunk_offset`, `stack`, `frame_stack_depth`, `current_op`). Or just expose a `step()` iterator on `VM`.
- Pyodide bridge: `rot_step_vm(source)` returning a stream of opcode-level snapshots.
- UI: replace or augment the `BytecodeView`'s static highlight with an IP marker that moves; add a tiny stack visualization (the top N values).
- Add a mode toggle: "Tree-walker step" vs "VM step" — let the user choose granularity.

This delivers the original HANDOFF promise that the playground shows compilation lower from AST → bytecode → execute, animated.

### 2. Address the "precode does not show fizzbuzz" report

Quick clarification with the user, then a small `OnboardingMessage` change to preview the source (or the first AST node's pretty-printed form) so the playground feels alive before the first step.

### 3. Finish M2's codegen surface

- `Slice` codegen + opcodes (`BUILD_SLICE`?).
- `Import` codegen — needs a `_loaded_modules` cache in the VM mirroring the tree-walker.
- Closures — `STORE_LOCAL` + upvalue cells. Big enough for its own Y if done properly.
- `finally` blocks — exception-flow correctness.
- Compound `IndexAssign` via `DUP_TOP_TWO`.

After this, the VM has 1:1 surface parity with the tree-walker and could be the default execution path.

### 4. Polish + content

- Cross-engine parity tests — run every example via both engines, diff their stdout.
- The "compound member assign" path in `codegen.py` uses `_BIN_OP_MAP.get(stmt.op)` which doesn't cover non-arithmetic ops; harmless today but worth a sanity check if `<<=` etc. were ever added.
- Examples gallery — more demonstrations. Particularly: a small program that exercises every M2 feature in one file, for parity testing.
- Documentation site updates — the `web/` `/docs` page is somewhat stale on M2.
- Paper update — the paper hasn't been touched since v2.25.13. Per user pref, paper is a final artifact near end of project — don't update it yet.

### 5. Smaller polish ideas (from past brainstorms)

- Snapshot diff between two pinned steps.
- Skip-to-next-output / skip-to-next-error buttons.
- Per-binding sparkline for numeric values across steps.
- Source-line gutter dots colored by execution.
- WASM ROT VM (eliminate the Pyodide 10MB cold-load).
- VS Code extension (syntax highlighting + run-on-save).

---

## User conventions / preferences (still apply)

- **Bump the version on every code change.** Patch (`Z`) for bug fixes and docs. Minor (`Y`) for new features. Major (`X`) for breaking changes. Update [`rot/__init__.py`](rot/__init__.py) `__version__` per commit.
- **Commit per change.** Each commit gets its own [`CHANGELOG.md`](CHANGELOG.md) entry at the top.
- **Tag every commit.** `git tag v2.X.Y`.
- **Run tests before each commit.** `python3 -m pytest tests/` (currently 807 passing).
- **Type-check the web side.** `cd web && npx tsc --noEmit`. Avoid `npm run build` (it dirties `.next/` and clashes with `npm run dev`).
- **Re-run `node web/scripts/copy-rot.mjs`** after any `rot/` change or version bump — the bundled `public/rot_package/*.py` powers the playground via Pyodide.
- **Action-oriented**: short messages mean "execute the obvious next step." When in doubt, use AskUserQuestion.
- **No emojis** in files unless explicitly requested.
- **No `--no-verify`, no force-push, no rewriting published history.**
- **Don't update [`paper/`](paper/) or major `web/` content** unless explicitly asked. Web/playground UI changes are fine; documentation overhauls aren't.
- **Use ruflo + jcodemunch MCPs** for non-trivial coding tasks and for codebase queries (per `/Users/omkar/CLAUDE.md`). The codebase is small (~5,000 LOC) so direct grep is also fine.

---

## Quick demo

```bash
# Tree-walker (default)
python3 -m rot examples/fizzbuzz.rot
python3 -m rot                          # REPL
python3 -m pytest tests/                # 807 passing

# Bytecode VM (M2)
python3 -m rot --vm examples/fizzbuzz.rot
python3 -m rot --vm examples/counter.rot
python3 -m rot --vm examples/factorial.rot

# Playground
cd web && npm install                    # one-time
cd web && npm run dev                    # http://localhost:3000

# Paper (don't touch unless asked)
cd paper && latexmk -pdf main.tex
```

---

## TL;DR for a new session

You're picking up ROT at **v2.27.17**, **807 tests passing**, all CI green. Both major milestones (M1 step-mode playground, M2 bytecode VM) have substantial shipped surface. The tree-walker remains the default execution path; the VM is opt-in via `python -m rot --vm` and runs all the examples that don't use slicing/import/finally/closures.

The playground at [`web/`](web/) has been thoroughly cleaned up: three phases (Read · Parse · Run), pretty-printed code in the Parse stage, opt-in Bytecode pane in animate mode, snapshot scrubbing timeline, keyboard navigation, persistent source + share-by-URL.

**The headline next-up:** wire VM step mode into the playground so the Bytecode pane animates per opcode (IP marker + stack visualization). That delivers the original HANDOFF promise of "watch your code compile to bytecode and execute opcode-by-opcode."

Also: the user reported "the precode does not show the fizzbuzz that automatically shows in source" right before asking for this handoff. Best guess is the Step Detail's onboarding state before any step — confirm with the user, then a small fix.

Honor conventions: bump version + tag per commit, run tests, run copy-rot, don't touch paper. Ask before any destructive git operation.
