# HANDOFF — Session context for ROT

A snapshot of project state, conventions, and the next strategic direction for a new Claude session picking up where the last one left off. Self-sufficient by design — read this and you have everything you need. For deeper context, see [`README.md`](README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`CHANGELOG.md`](CHANGELOG.md) (newest first), [`BUG_REPORT.md`](BUG_REPORT.md) (the v2.13.0 audit), and [`paper/main.pdf`](paper/main.pdf) (the design retrospective).

## TL;DR

ROT is at **v2.25.17**, 628 tests passing, all CI green. The language is feature-complete enough as a small Python-flavored interpreter: `let`, `finally`, slicing, f-string format specs, rustc-style errors, 35+ builtins, ROT-style output, info-leak hardening, immutable builtins. The v2.13.0 audit's ~600 findings were worked through by 12 sequential agents across v2.14 → v2.25; most are fixed.

**The next chapter is the language's identity.** ROT becomes *"the language whose playground IS a compiler textbook"* — write any program, watch every transformation animated step by step. See characters group into tokens, tokens form an AST, AST lower to bytecode opcodes, opcodes execute on a stack. Cross-linked, narratable, runnable in any browser.

**Start at Milestone 1: convert the interpreter to a generator-based step mode.** Details in [§ Milestone 1 — deep dive](#milestone-1--deep-dive) below. Every later milestone depends on it.

---

## The vision

ROT is small enough to read in an afternoon (~3,800 LOC across [`rot/`](rot/)), robust enough to pass 628 tests, and visualizable enough to make compilation tangible. The combination is distinctive:

- **Godbolt** shows source → assembly, but it's static.
- **AST viewers** exist for many languages, but they show one stage in isolation.
- **Crafting Interpreters** (Nystrom) teaches compilation in text, but it's not interactive.
- Nobody has packaged *"compilation as a live animated explainer for any user input."*

That's the niche. Tagline candidates:

- "Watch your code compile."
- "A language built to be read, not just run."
- "The compiler that explains itself."

The playground (already at [`web/`](web/)) becomes the canonical surface. Running ROT outside the playground stays valid; running it INSIDE the playground is the demo.

## What ROT is (today)

- **Surface:** C++/Python-flavored hybrid. `funct` for `def`, `cout`/`coutln` for `print`, `|` as parameter/arg separator, `this` not `self`, `//` comments, C-style braces.
- **Pipeline:** source → hand-rolled char-by-char lexer → recursive-descent parser (Pratt for expressions) → AST → tree-walking interpreter. No `exec()` since v2.0.0. The standalone emitter that briefly produced Python source was removed in v2.23.0.
- **Repo:** https://github.com/omkarxpatel/ROT
- **CI:** GitHub Actions, `pytest` across Python 3.9 / 3.10 / 3.11 / 3.12.
- **Version:** see [`rot/__init__.py`](rot/__init__.py); currently `2.25.17`.

## Project layout

```
rot/                  the language package (~3,800 LOC)
├── __init__.py       __version__
├── __main__.py       `python -m rot` entry
├── cli.py            argparse CLI; default starts REPL
├── compiler.py       orchestrates lex → parse → interpret
├── lexer.py          hand-rolled char-by-char tokenizer
├── token.py          Token dataclass (lexeme, kind, line, col)
├── keywords.py       KEYWORDS dict (incl. let, finally, super)
├── ast.py            AST node dataclasses; every node carries line/col
├── syntax.py         recursive-descent parser; Pratt for expressions
├── interpreter.py    tree-walking interpreter + Environment + RotClass/Instance/BoundMethod
├── builtins.py       standard library (35+ builtins)
├── repl.py           interactive REPL with multi-line + persistent history
└── errors.py         RotError + rustc-style rendering
tests/                628 tests (per-layer + end-to-end + CLI + REPL + compiler)
examples/             7 .rot programs with .expected golden outputs
paper/                10-page LaTeX design retrospective (main.pdf included)
web/                  Next.js 15 + Pyodide site: landing / docs / playground / paper PDF
ARCHITECTURE.md       deep design doc
CHANGELOG.md          per-release notes (newest first)
BUG_REPORT.md         v2.13.0 audit (~600 findings; most fixed in v2.14-v2.25)
HANDOFF.md            this file
```

## What ROT can do (as of v2.25.17)

- Variables; compound assignment (`+= -= *= /= %=`)
- **`let name = expr`** (v2.16.6) — fresh-local binding. Bare `=` chain-walks per the v2.10.0 closure-mutation design.
- Numbers (int, float), strings with escapes, booleans (`true`/`false`), `null`
- Arithmetic, comparison, logical (`and`/`or`/`not`), modulo, unary `-`
- Conditionals: `if` / `elseif` / **`else if`** (v2.25.4) / `else`
- Loops: `while`, `for x in iter`, `break`, `continue` (lexically scoped to enclosing function since v2.15.1)
- Functions (`funct`), recursion, closures that mutate enclosing scope (or use `let` to shadow)
- Classes (`class`, `this`, `init`, methods, fields)
- Lists `[a | b | c]`, dicts `{k: v | k2: v2}`, member access `obj.attr`
- **Slicing** `xs[a:b:c]` (v2.25.9). Negative bounds wrap; reverse with `[::-1]`.
- Error handling: `try` / `catch` / **`finally`** (v2.25.5) / `throw`
- **f-string format specs** `f"{pi:.2f}"`, `f"{n:>5}"` (v2.25.10)
- Module system: `import "path"` (relative, cached, cycle-safe since v2.25.3)
- Interactive REPL (`python -m rot`)
- **rustc-style errors** (v2.22.7) — source line + caret + Python-ism hints (`print` → "did you mean 'cout'?")
- **Immutable builtins** (v2.16.5) — `pi = 3.0` is rejected; use `let pi = 3.0` to shadow
- **35+ builtins**: I/O (`cout`, `coutln`, `input`, `read_file`, `write_file`), conversion (`str`, `num`, `chr`, `ord`), math (`abs`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `round`, `pi`, `e`), collections (`len`, `range`, `append`, `pop`, `sum`, `sorted`, `reversed`, `keys`, `values`, `items`), introspection (`type`, `is_num`/`is_str`/`is_list`/`is_dict`/`is_bool`/`is_null`/`is_func`), random (`rand_int`, `rand_float`, `seed`), control (`assert`, `exit`).

## How we got here

The v2.13.0 codebase was audited: ~600 findings in [`BUG_REPORT.md`](BUG_REPORT.md) across lexer, parser, interpreter, builtins, emitter drift, CLI/REPL, and test coverage. **Twelve sequential agents** worked through the findings, each owning a minor version (`Y`) with one patch (`Z`) per fix. 81 commits, 81 tags, tests 201 → 628. Headline outputs:

- Python-error leaks wrapped (v2.14.x — 12 fixes)
- Break/continue function-boundary escape fixed (v2.15.x)
- `let` keyword + scoping discipline (v2.16.x)
- Compound-assign error wrapping (v2.17.x)
- Info-leak hardening — dunder filter, RotClass.get_member (v2.18.x)
- REPL hardening — `_needs_more`, Ctrl-C, exit/history (v2.19.x)
- Lexer fixes — state reset, CR/CRLF, BOM, friendly errors (v2.20.x)
- ROT-style output — `_stringify` for collections, `RotInstance.__str__`, type(class) (v2.21.x)
- Source locations on AST + rustc-style rendering (v2.22.x)
- Emitter deletion (v2.23.0)
- Test coverage backfill — test_cli, test_compiler, test_repl (v2.24.x)
- Missing features — `else if`, `try/catch/finally`, slicing, format specs, `super` reserved, 10 new builtins (v2.25.x)

Plus:
- Paper draft (v2.25.13): 10-page LaTeX in [`paper/`](paper/) — design retrospective. **Final paper is meant to ship near end of project; don't keep updating it unless asked.**
- Web playground (v2.25.14): Next.js + Pyodide site in [`web/`](web/), runs ROT in-browser.
- Expanded site (v2.25.15): landing / docs / playground / paper PDF — same `web/` directory.

## The pipeline today (3 stages visualized)

The playground currently shows three stages:

```
[Source] → [Tokens] → [AST] → [Execution output]
```

For a 2-line program `x = 5\ncoutln(x + 3)`:

1. **Lexer** ([`rot/lexer.py`](rot/lexer.py)): 15 tokens, color-coded chips in the Tokens pane.
2. **Parser** ([`rot/syntax.py`](rot/syntax.py)): `Program(body=[Assign("x", NumberLit(5)), ExprStmt(Call(Identifier("coutln"), [BinaryOp("+", Identifier("x"), NumberLit(3))]))])`. Rendered as a collapsible tree.
3. **Interpreter** ([`rot/interpreter.py`](rot/interpreter.py)): walks the AST recursively. Output `8` appears in the Output pane.

The visualization is static — user clicks Run, all three panes populate at once.

## The pipeline tomorrow (5 stages, animated, cross-linked)

```
[Source] → [Tokens] → [AST] → [Bytecode] → [Execution]
```

Two new stages (**Bytecode** between AST and Execution; **Execution** becomes a stack-machine animation, not just output). Plus:

- **Animation:** stage transitions animate. Tokens fly in. AST grows. Opcodes emit. VM pointer walks.
- **Cross-linking:** hover any artifact in any pane → highlights the corresponding pieces in every other pane. Click `8` in output → highlights the `+` in source, the `BinaryOp` in AST, the `ADD` opcode in bytecode.
- **Explainer copy:** as each stage runs, a side panel writes one or two sentences explaining what's happening ("the lexer reads characters and groups them into tokens; identifiers, keywords, numbers, operators").
- **Step controls:** play, pause, step forward, step backward, speed slider.

That's the headline experience. Recruiters / educators / curious people see compilation made legible.

## Roadmap — 4 milestones

Each milestone is shippable on its own and produces a demo-able artifact.

### Milestone 1 — Step-mode interpreter + live env pane (~2 weeks)
*Foundation.* Generator-based interpreter; playground env pane.

### Milestone 2 — Bytecode compiler + VM + bytecode pane (~3 weeks) — **the headline**
The new compilation stage. ~30 opcodes; stack-based VM. Bytecode pane in the playground.

### Milestone 3 — Cross-link everything (~2 weeks)
All UI work. Hover any token/AST node/opcode/output value → highlight every related artifact across panes.

### Milestone 4 — Time travel + provenance (~2 weeks)
Record state diffs in the VM; step backward. Provenance: every value remembers its source span and the opcodes that produced it.

**Total to "watch your code compile":** ~9 weeks part-time. The first demo-able win (Milestone 1) is ~2 weeks.

---

## Milestone 1 — deep dive

**Goal.** Convert the tree-walking interpreter from a "run to completion" model to a "step one statement at a time" model. Add a live environment pane to the playground that updates after each step.

**Why this first.**

1. Smallest delta. No new module — just a generator-based rewrite of `_execute_statement` and `_evaluate`.
2. Foundation for every later milestone. Milestone 2 (bytecode VM) needs to step too. Milestone 4 (time travel) needs snapshots. Milestone 3 (cross-linking) needs to know what's currently executing.
3. First demo-able win. Even just env-pane-live-updates makes the playground noticeably more interesting.

### Generator API design

Today:

```python
class Interpreter:
    def execute(self, program: ast.Program) -> None:
        for stmt in program.body:
            self._execute_statement(stmt)
```

After Milestone 1:

```python
class Interpreter:
    def execute(self, program: ast.Program) -> None:
        # Fast path: run to completion, no snapshots. Unchanged for CLI.
        for stmt in program.body:
            self._execute_statement(stmt)

    def iter_execute(self, program: ast.Program) -> Iterator[Snapshot]:
        # Step mode: yield a snapshot after each top-level statement.
        # Used by the playground.
        for stmt in program.body:
            self._execute_statement(stmt)
            yield self._snapshot(stmt)
```

For Milestone 1, **statement-level granularity is enough**. Expression-level stepping (yielding between operands of a `BinaryOp`) can come in Milestone 3 or 4 — much more involved (turns `_evaluate` into a generator-coroutine and requires a stack of generators), and only useful once we have the bytecode VM where each opcode is the natural step granularity.

### Snapshot shape

```python
@dataclass
class Snapshot:
    """State of the interpreter after executing one statement."""
    statement_line: int
    statement_col: int
    statement_kind: str        # "Assign", "Call", "IfStmt", etc.
    env: list[EnvFrame]        # outermost to innermost
    output_since_last: str     # captured stdout since previous snapshot
    error: str | None = None   # if execution halted with an error

@dataclass
class EnvFrame:
    scope_kind: str            # "global", "function", "method", "block"
    scope_label: str           # e.g. "global" or "funct foo" or "method Counter.tick"
    bindings: dict[str, Any]   # variable name -> rot value
```

Returned outermost-first. Builtins env is implicit (frozen, doesn't change) and excluded from snapshots.

### Output capture

Today `cout` and `coutln` print to `sys.stdout` directly. For step mode, the interpreter should own a `StringIO` buffer that `cout`/`coutln` write to instead. Between snapshots, drain the buffer into `output_since_last`.

Implementation: add a `self._capture_buffer: io.StringIO | None = None` to the interpreter. Modify `_builtin_cout` and `_builtin_coutln` to write to it if set, else to `sys.stdout`. `iter_execute` sets it on entry, drains it per statement, clears on exit.

Alternative: `contextlib.redirect_stdout` in `iter_execute`. Cleaner but slightly less control. Either works.

### Playground UI changes (in [`web/src/app/playground/page.tsx`](web/src/app/playground/page.tsx))

- **New toggle:** "Run" / "Animate" mode. Default to Run for fast execution; user clicks Animate to switch to step mode.
- **In Animate mode:** the Run button becomes "Step" (one statement) plus "Play" (auto-step at speed N). Add a speed slider (50ms–2000ms per step).
- **New pane: Env.** Renders the scope stack. Each scope is a card showing variable name → value. Recent changes flash green for one step (new binding) or yellow (mutation).
- **Source highlight:** the currently-executing statement's span (`line`, `col`) is highlighted in the CodeMirror editor. Use a CodeMirror decoration.

The Pyodide bridge in [`web/src/lib/pyodide-runtime.ts`](web/src/lib/pyodide-runtime.ts) needs a new entry point:

```python
def rot_step(source):
    """Generator function that yields snapshots dict-by-dict."""
    tokens = Lexer().tokenize(source)
    program = Parser(tokens).parse()
    interp = Interpreter()
    interp._capture_buffer = io.StringIO()
    for snapshot in interp.iter_execute(program):
        yield {
            "statement_line": snapshot.statement_line,
            "statement_col": snapshot.statement_col,
            "statement_kind": snapshot.statement_kind,
            "env": [{"scope_kind": f.scope_kind, "scope_label": f.scope_label, "bindings": dict(f.bindings)} for f in snapshot.env],
            "output_since_last": snapshot.output_since_last,
            "error": snapshot.error,
        }
```

JS side calls this as a Python async generator and pumps it one yield at a time.

### Test plan

In [`tests/test_interpreter.py`](tests/test_interpreter.py), new section:

- `test_iter_execute_yields_one_snapshot_per_statement`
- `test_iter_execute_snapshots_show_progressive_env`
- `test_iter_execute_captures_output_per_statement`
- `test_iter_execute_handles_control_flow_through_function_call`
- `test_iter_execute_handles_loops_yield_per_iteration_body`  # if for/while bodies should snapshot per statement inside
- `test_iter_execute_error_in_middle_yields_error_snapshot`
- `test_execute_unchanged_after_iter_execute_added` (regression: the fast path still passes all existing tests)

### Suggested Z bumps

The convention from v2.14.x–v2.25.x: one fix per Z, commit + tag per Z, run tests before each commit, no `--no-verify`, no force-push, all conventions in [`/Users/omkar/CLAUDE.md`](file:///Users/omkar/CLAUDE.md) apply.

A reasonable Z breakdown for Milestone 1:

- **v2.26.0** — Schema: `Snapshot` and `EnvFrame` dataclasses + `Interpreter.iter_execute` skeleton (yields empty snapshots; fast path unchanged). Y bump to v2.26 marks the strategic shift; subsequent fixes within Milestone 1 are patches.
- **v2.26.1** — Env snapshot serializer (`_env_snapshot` method on Environment). Walks the chain, returns the structured list.
- **v2.26.2** — Output capture via `self._capture_buffer`. Modify `_builtin_cout`/`_builtin_coutln`.
- **v2.26.3** — Wire snapshots: `iter_execute` calls `_snapshot(stmt)` and yields it. Tests confirm statement-by-statement state.
- **v2.26.4** — Pyodide bridge: `rot_step(source)` Python generator + JS-side async iterator wrapper.
- **v2.26.5** — Playground: Animate-mode toggle + Step button + speed slider.
- **v2.26.6** — Playground: Env pane rendering (scope stack + binding cards).
- **v2.26.7** — Playground: source-highlight of currently-executing statement (CodeMirror decoration).
- **v2.26.8** — Polish: explainer copy ("the interpreter just bound `x = 5`"), recently-changed visual cues (green/yellow flashes).

### Acceptance criteria

When Milestone 1 is done:

1. `python -m pytest tests/` still passes (all 628 + new tests).
2. `python -m rot examples/fizzbuzz.rot` produces identical output to before.
3. In the playground, the user can:
   - Toggle Animate mode.
   - Click Step. The first statement runs. The Env pane shows a single scope ("global") with one binding (e.g. `x = 5`). The output pane shows no output yet.
   - Click Step again. The second statement runs. Output pane appends `8`.
   - Click Play. Steps auto-advance.
   - See the source-highlight move from line 1 to line 2 as steps proceed.

### What's NOT in Milestone 1

- Bytecode pane — that's Milestone 2.
- Step backward / time travel — that's Milestone 4.
- Cross-pane hover highlighting — that's Milestone 3.
- Expression-level stepping — possibly Milestone 3 or 4.
- Explainer text for every concept — minimal text in M1; expanded in M3.

---

## Milestone 2 — bytecode VM (sketch)

The headline. Adds a new stage between AST and Execution.

**Files to create:**
- [`rot/codegen.py`](rot/codegen.py) — AST → bytecode compiler.
- [`rot/vm.py`](rot/vm.py) — stack-based VM that runs bytecode.
- [`rot/opcodes.py`](rot/opcodes.py) (optional) — opcode enum.

**Files to modify:**
- [`rot/compiler.py`](rot/compiler.py) — `Compiler` should optionally run via VM instead of tree-walker. Add `Compiler(use_vm=True)` flag.
- [`rot/cli.py`](rot/cli.py) — optional `--vm` flag to switch engines.

**Proposed opcode set (~30):**

```
# Stack manipulation
LOAD_CONST <idx>       push constant from pool
LOAD_NULL              push null
LOAD_TRUE              push true
LOAD_FALSE             push false
POP                    pop top of stack
DUP                    duplicate top
SWAP                   swap top two

# Variables
LOAD_NAME <name>       push value bound to name (env chain walk)
STORE_NAME <name>      pop, bind name (chain-walking)
STORE_LOCAL <name>     pop, bind name (always local)  # for `let`

# Arithmetic / comparison
ADD, SUB, MUL, DIV, MOD, NEG, NOT
EQ, NE, LT, LE, GT, GE
AND, OR  # short-circuit; emitted with JUMP_IF_FALSE+POP+rhs+...

# Control flow
JUMP <offset>          unconditional
JUMP_IF_FALSE <offset>
JUMP_IF_TRUE <offset>
CALL <argc>            call top-of-stack-but-one with argc args (popped above)
RETURN                 return from current frame; top of stack is value
RETURN_NONE            return null

# Aggregate types
BUILD_LIST <count>
BUILD_DICT <count>
GET_INDEX              pop index, pop target, push target[index]
SET_INDEX              pop value, pop index, pop target, target[index] = value
GET_MEMBER <name>      pop target, push target.name
SET_MEMBER <name>      pop value, pop target, target.name = value

# Control flow signals
RAISE                  pop value, raise as throw
BEGIN_TRY <handler_offset>
END_TRY
```

That's ~30. Exact count and naming TBD during M2 design; *Crafting Interpreters* Part III is the textbook reference and worth a re-read at that point.

**Compiler architecture:** `codegen.py` defines a `Compiler` class that walks the AST and emits opcodes into a `Chunk` (bytecode list + constant pool + line-mapping). One method per AST node type. Functions are compiled into their own `Chunk` and stored as constants.

**VM loop:** `vm.py` defines a `VM` class with an instruction pointer, a stack, an environment chain, and a frame stack for function calls. Main loop: `while ip < len(code): dispatch(code[ip])`.

**Bytecode pane in the playground:** new pane showing `<offset> <opcode> <args>` per line. Instruction pointer highlights as VM executes. Stack visualization alongside (small panel showing the top N values).

**Tree-walker stays.** It's the reference; tests cover both engines. CI runs both.

**Effort:** ~3 weeks part-time including tests for both engines and the bytecode pane UI.

---

## Milestone 3 — cross-link everything (sketch)

All UI work. Every artifact in every pane needs to know its provenance:

- A token knows its character range in source and which AST node it became part of.
- An AST node knows its token range and which opcode(s) it lowered to.
- An opcode knows its source AST node and (when executed) which output it produced.
- An output line knows the opcode(s) and AST nodes that produced it.

Implementation: each artifact carries IDs. A central "selection bus" — when one artifact is hovered, every pane queries the bus for matching IDs and highlights them.

**Effort:** ~2 weeks part-time. No language changes; pure web work.

---

## Milestone 4 — time travel + provenance (sketch)

The VM records a state diff per opcode. The playground gains a Rewind button. Scrubbable timeline.

Provenance is the deeper feature: every runtime value is wrapped in `(value, origin)` where origin is the AST node + opcode that produced it. Hover an output value, see its full computation history.

**Effort:** ~2 weeks part-time.

---

## User conventions / preferences

The user (Omkar) is the project owner. The following are durable preferences observed across the v2.13 → v2.25 sweep. Honor them without re-asking.

- **Bump the version on every code change.** Patch (`Z`) for bug fixes and docs. Minor (`Y`) for new features. Major (`X`) for breaking changes. Update [`rot/__init__.py`](rot/__init__.py) `__version__` per commit.
- **Commit per change.** Don't batch unrelated changes. Each commit gets its own [`CHANGELOG.md`](CHANGELOG.md) entry at the top.
- **Tag every commit.** `git tag v2.X.Y` after each commit. Always push tags.
- **Action-oriented.** "okay" or "go" means "execute the plan." If it's clearly the right next step, just do it.
- **Y-per-agent scheme for large sweeps.** When dispatching parallel/sequential agents to work through a batch, each agent owns one `Y` (minor version) and each fix is a `Z` (patch) within it. Cluster bugs by type, not by file.
- **Style preference:** concise prose, structured tables, real code examples over abstractions.
- **Tooling preference:** avoid over-engineering. Flat `rot/` package (no `src/`). Add tooling only when forced.
- **No emojis in files.** Per global [`/Users/omkar/CLAUDE.md`](file:///Users/omkar/CLAUDE.md).
- **No `--no-verify`, no force-push, no rewriting published history.**
- **Run tests before each commit.** `python3 -m pytest tests/` must pass.
- **Don't auto-update [`paper/`](paper/) or [`web/`](web/) on every code change.** Update them only when a meaningful batch has accumulated (major features, milestone shifts). **The paper is meant to be a final artifact near the end of the project** — leave it mostly alone until the user explicitly signals the end-of-project polish phase. The site can be refreshed when user-visible language surface changes (new keyword needs a docs entry; the [CodeBlock keyword tables in `web/src/components/code-block.tsx`](web/src/components/code-block.tsx) need to stay in sync for highlighting). The version pill on the site auto-updates from [`rot/__init__.py`](rot/__init__.py) via [`scripts/copy-rot.mjs`](web/scripts/copy-rot.mjs).

## Repo conventions

- `funct` not `def`, `cout`/`coutln` not `print`, `|` not `,`, `this` not `self`, `//` for comments, C-style braces.
- Identifiers: `[A-Za-z_][A-Za-z_0-9]*`.
- Output style: rot-flavored. `cout`/`coutln` print `null` not `None`, `true`/`false` not `True`/`False`. Lists render as `[a | b | c]`. Dicts as `{"k": v | "k2": v2}`. Instances as `<instance of ClassName>` (overridable via a `to_string()` method).
- **Closures can mutate enclosing scope** (chain-walking `Environment.set`) — the v2.10.0 intentional design. Use `let name = expr` (v2.16.6) to opt out and create a fresh local.
- **Method params and `this` use `set_local`** — they don't pollute enclosing scope.
- **Builtins are immutable** (v2.16.5) — `pi = 3.0` is rejected. Use `let pi = 3.0` to shadow within a local scope.
- **`break` / `continue`** are lexically scoped to loops in the SAME function body (v2.15.1) — they cannot escape across a function call boundary.
- **All runtime errors carry source location** (v2.22.3) — `InterpreterError` is rendered rustc-style by the CLI/REPL when source is available.
- **No Python info leak via member access** (v2.18.x) — `obj.__class__`, `obj._private`, `bytes` returns are all rejected.

## Quick demo

```bash
# Language
python3 -m rot examples/fizzbuzz.rot   # run a program
python3 -m rot                          # REPL
python3 -m rot --no-run file.rot        # validate
python3 -m rot --trace file.rot         # show lex / parse / interp stages
python3 -m pytest tests/                # 628 passing

# Web site (Next.js, runs ROT in browser via Pyodide)
cd web && npm install                   # one-time
cd web && npm run dev                   # http://localhost:3000

# Paper
cd paper && latexmk -pdf main.tex       # rebuilds main.pdf
```

## Open items / known follow-ups (small)

These are pre-existing minor items from the v2.13 audit that didn't fit any agent's scope. Not blocking Milestone 1.

- **Closure late-binding.** `for i in [1|2|3] { funct f() { return i } append(fns, f) }` produces three closures that all see `i == 3` (Python footgun, inherited). Either pin current behavior or fix with per-iteration capture.
- **REPL tab completion** — skipped in v2.19.x as optional.
- **Inheritance / `super`** — `super` is reserved (v2.25.7) with a clear "not supported" error, but no implementation. Single-inheritance is a natural minor.
- **Multi-line strings** (triple-quoted).
- **Integer division `//`** — deferred in v2.25.6 because `//` is the comment marker. Could pick a different syntax (`~/`, `\\`) but a builtin `floor(a / b)` already exists.
- **TCO** in the interpreter for deep recursion.
- **Stats on the landing page are hardcoded** — `~3,800` LOC, `628` tests, `81+` commits. Easy to wire to build-time computed values if you want.

## Out of scope (for now)

- **Don't refresh [`paper/`](paper/)** — the paper is final-near-end-of-project. Leave it alone unless explicitly asked.
- **Don't keep [`web/`](web/) in lockstep with every code change.** Only refresh on big milestones — when a new keyword needs a docs entry, or when a milestone (M1, M2, etc.) ships and the docs need updating. The version pill auto-updates; everything else is manual.

## TL;DR for a new session

You're picking up ROT at **v2.25.17**, 628 tests passing, all CI green. The language is feature-complete for a small interpreted language. **The next chapter is making compilation visible** — turning the playground at [`web/`](web/) into a live animated compiler explainer where any user can write any program and watch every stage (lex → parse → AST → bytecode → execute) animate, cross-link, and explain itself.

The path is four milestones. **Start with Milestone 1**: rewrite [`rot/interpreter.py`](rot/interpreter.py)'s `_execute_statement` as a generator that yields a snapshot after each statement. Then build the playground's Env pane and step controls. Concrete deep-dive in [§ Milestone 1 — deep dive](#milestone-1--deep-dive) above. Suggested first commit is **v2.26.0** — the Y bump marks the strategic shift to compilation visibility.

Honor the user's conventions. Don't touch [`paper/`](paper/). Don't refresh [`web/`](web/) until M1 actually ships. Ask before any destructive git operation.
