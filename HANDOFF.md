# HANDOFF — Session context for ROT

A snapshot of project state and conventions for a new Claude session picking up where the last one left off. For deeper detail, see [`README.md`](README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), [`CHANGELOG.md`](CHANGELOG.md), and the v2.13.0 audit at [`BUG_REPORT.md`](BUG_REPORT.md).

## What ROT is

A custom programming language built as a learning project and portfolio piece.

- **Surface:** C++/Python-flavored hybrid. `funct` for `def`, `cout` / `coutln` for `print`, `|` as parameter/arg separator, `this` not `self`, C-style braces, `//` comments.
- **Pipeline:** source → hand-rolled char-by-char lexer → recursive-descent parser (Pratt for expressions) → AST → tree-walking interpreter. Python `exec()` has been gone since v2.0.0; the standalone emitter was removed in v2.23.0.
- **Current version:** see [`rot/__init__.py`](rot/__init__.py). At time of writing: `2.25.11`.
- **GitHub:** https://github.com/omkarxpatel/ROT
- **CI:** GitHub Actions running `pytest` across Python 3.9 / 3.10 / 3.11 / 3.12.

## Project layout

```
rot/                    # the language package (~2,900 LOC)
├── __init__.py         #   __version__
├── __main__.py         #   `python -m rot` entry
├── cli.py              #   argparse CLI; default starts REPL if no file
├── compiler.py         #   orchestrates lex → parse → interpret
├── lexer.py            #   hand-rolled char-by-char tokenizer
├── token.py            #   Token dataclass (lexeme, kind, line, col)
├── keywords.py         #   KEYWORDS dict (incl. let, finally, super)
├── ast.py              #   AST node dataclasses; every node carries line/col
├── syntax.py           #   recursive-descent parser; Pratt for expressions
├── interpreter.py      #   tree-walking interpreter + Environment + RotClass/Instance/BoundMethod
├── builtins.py         #   standard library (cout, len, math, file I/O, sum, sorted, chr, ord, ...)
├── repl.py             #   interactive REPL with multi-line input + persistent history
└── errors.py           #   RotError / LexerError / ParserError / InterpreterError + rustc-style rendering
tests/                  # 628 tests, pytest. Per-layer + end-to-end + CLI/REPL/compiler.
examples/               # 7 working .rot programs with .expected golden outputs
ARCHITECTURE.md         # deep design doc
CHANGELOG.md            # per-release notes (read newest first)
BUG_REPORT.md           # v2.13.0 exhaustive audit (~600 findings); most are fixed in v2.14–v2.25
README.md               # short overview + badges
pyproject.toml          # pytest pythonpath config
.github/workflows/      # GHA CI workflow
```

## What ROT can do (as of v2.25.11)

- Variables, compound assignment (`+= -= *= /= %=`)
- **Explicit-shadow `let name = expr`** (v2.16.6) — fresh-local binding; bare `=` keeps the v2.10.0 chain-walk semantics
- Numbers (int + float), strings (with escapes), booleans (`true` / `false`), `null`
- Arithmetic, comparison, logical (`and` / `or` / `not`), modulo, unary `-`
- Conditionals: `if` / `elseif` / **`else if`** (two-word form, v2.25.4) / `else`
- Loops (`while`, `for x in iter`), `break`, `continue` (now correctly scoped to enclosing function, v2.15.1)
- Functions (`funct`), return values, recursion, closures that mutate enclosing scope
- Classes (`class`, `this`, `init`, methods, fields, instances)
- Lists `[a | b | c]`, indexing, mutation, iteration, **slicing `xs[a:b:c]`** (v2.25.9)
- Dicts `{k: v | k2: v2}`, member access `obj.attr`
- Error handling: `try` / `catch` / `throw` / **`finally`** (v2.25.5)
- String interpolation: `f"hello, {name}"` with **format specs** (v2.25.10) — `f"{pi:.2f}"`, `f"{x:>5}"`
- Module system: `import "path"` (relative, cached, circular-import-safe since v2.25.3)
- Interactive REPL (`python -m rot` with no file) — multi-line strings, `exit`/`quit`/`:q`, persistent `~/.rot_history`
- **rustc-style errors** (v2.22.7) — source line + caret + `(did you mean 'cout'?)` hints for Python-isms
- **~35 builtins** including:
  - I/O: `cout`, `coutln`, `input`, `read_file`, `write_file`
  - Conversion: `str`, `num`, `chr`, `ord`
  - Math: `abs`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `round`, `pi`, `e`
  - Collections: `len`, `range`, `append`, `pop`, `sum`, `sorted`, `reversed`, `keys`, `values`, `items`
  - Type introspection: `type`, `is_num`/`is_str`/`is_list`/`is_dict`/`is_bool`/`is_null`/`is_func`
  - Random: `rand_int`, `rand_float`, `seed`
  - Control: `assert`, `exit`

## Recent session: what happened

The v2.13.0 codebase was given an exhaustive multi-layer audit producing [`BUG_REPORT.md`](BUG_REPORT.md) — ~600 findings spanning lexer, parser, interpreter, builtins, emitter drift, CLI/REPL, and test coverage. Then **12 specialized agents** worked through the findings sequentially, each owning a minor version (`Y`) with one patch (`Z`) per fix:

| Y | Agent scope | Z count | Test delta |
|---|---|---|---|
| **2.14.x** | Safety net — wrap every Python-error leak (`TypeError`/`ValueError`/`ZeroDivisionError`/`RecursionError`/`OSError`/`UnicodeDecodeError`). Forced `encoding="utf-8"` on all file I/O. | 12 | 201 → 260 |
| **2.15.x** | Control-flow escape — `break`/`continue` no longer escape across function boundaries; uncaught `throw` no longer leaks as `_ThrowSignal`. | 2 | 260 → 270 |
| **2.16.x** | Declaration scoping — `funct`/`class`/catch-var use `set_local`; builtins live in a frozen layer (`pi = 3.0` now errors); reject reassigning `this`; **new `let` keyword**. | 6 | 270 → 298 |
| **2.17.x** | Compound-assign + dict/string errors — `x /= 0`, `s[0] /= 0`, `c.x /= 0` now wrap cleanly; strings-are-immutable message; dict-key-not-found message. | 5 | 298 → 310 |
| **2.18.x** | Info-leak hardening — `_`-prefixed member access blocked; `RotClass`/`BoundMethod` have their own `get_member` (no Python `getattr` fallback); `bytes` return from Python methods rejected; `dict_keys`/`dict_values`/`dict_items` report as `"list"`; user-class type names wrapped in `<>` to avoid colliding with primitives. | 6 | 310 → 339 |
| **2.19.x** | REPL hardening — `_needs_more` tracks open strings and skips `//` comments; `Ctrl-C` no longer swallowed; `exit`/`quit`/`:q` commands; `~/.rot_history`; EOF-during-continuation warns; strings echo with quotes, `null` echoes as `null`. | 7 | 339 → 379 |
| **2.20.x** | Lexer fixes — state reset on re-`tokenize`; bare-CR/CRLF line tracking; f-string brace-depth at lex time; UTF-8 BOM strip; friendly hints for `;`, `&`, `~`, `===`, `'`, etc.; `_log` width safe; trailing-backslash hint. | 10 | 379 → 411 |
| **2.21.x** | ROT-style output — `_stringify` recurses through lists/dicts with `|`-separators; `RotInstance` renders as `<instance of X>` with a `to_string()` override hook; `RotFunction`/`RotClass`/`BoundMethod` get readable forms; cycle detection. | 6 | 411 → 461 |
| **2.22.x** | Source locations — every AST node carries `line`/`col`; `InterpreterError` raises thread them through via `_locate` dispatcher wrappers; parser errors carry locations too; friendly token-display names (`'('` not `L_PAREN`); Python-ism hints (`print` → "did you mean 'cout'?"); **rustc-style source + caret rendering**. | 7 | 461 → 496 |
| **2.23.0** | Emitter deletion — `rot/emitter.py` and `tests/test_emitter.py` gone. Removed 40 drift findings from the report at zero cost. | 1 | 496 → 484 |
| **2.24.x** | Test backfill — new `tests/test_cli.py`, `tests/test_compiler.py`; expanded `test_repl.py`; closure/recursion/equality/indexing/import edges; v2.13.0 BoundMethod fix tested for regular methods (was only `init`). | 8 | 484 → 531 |
| **2.25.x** | Missing features — `else if`, `try/catch/finally`, slicing (`s[a:b:c]`), f-string format specs, `super` reserved with clear error, 10 new builtins (`sum`/`sorted`/`reversed`/`keys`/`values`/`items`/`chr`/`ord`/`seed`/`exit`), import-cycle fix, REPL `Call`-echo suppression, `return f"..."` fix. | 10 + 1 hotfix | 531 → 628 |

**81 commits, 81 tags, all pushed to `origin/main`.** CI green on v2.25.11 (the +1 hotfix patched a Python 3.12 incompatibility surfaced by CI: `slice` became hashable in 3.12, so `dict[slice]` raises `KeyError` not `TypeError` — our slice handler now intercepts dict targets explicitly).

## User conventions / preferences

The user (Omkar) is the project owner. Things to know:

- **Bump the version on every code change.** Patch for bug-fixes/docs, minor for new features, major for breaking changes. Every commit gets a matching git tag (`v2.25.11` etc.). Always push tags.
- **Commit per change.** Don't batch unrelated changes. `CHANGELOG.md` gets updated alongside each bump.
- **Action-oriented.** "okay" or "go" means "execute the plan." Doesn't want constant confirmation; if it's clearly the right next step, just do it. If a real design question comes up, ask.
- **Y-per-agent scheme for large sweeps.** When dispatching multiple parallel/sequential agents, each agent owns one `Y` (minor version) and each fix is a `Z` (patch) within it. Cluster bugs by type, not by file.
- **Style preference:** concise prose, structured tables, real code examples over abstractions.
- **Tooling preference:** avoid over-engineering. Flat `rot/` package (no `src/`), `pyproject.toml` only added when pytest forced it.
- **No emojis in files** unless requested (per global `CLAUDE.md`).
- **No `--no-verify`, no force-push, no rewriting published history.**

## Repo conventions

- `funct` not `def`, `cout` / `coutln` not `print`, `|` not `,` for arg/param separator, `this` not `self`, `//` for comments, C-style braces.
- Identifiers: `[A-Za-z_][A-Za-z_0-9]*`.
- Output style: rot-flavored. `cout` / `coutln` print `null` not `None`, `true` / `false` not `True` / `False`. Lists render as `[a | b | c]`. Dicts as `{"k": v | "k2": v2}`. Instances as `<instance of ClassName>` (overridable via `to_string()`).
- **Closures can mutate enclosing scope** (chain-walking `Environment.set`) — this is the v2.10.0 intentional design. Use `let name = expr` (v2.16.6) to opt out and create a fresh local.
- **Method params and `this` use `set_local`** — they don't pollute the enclosing scope.
- **Builtins are immutable** (v2.16.5) — `pi = 3.0` is rejected. Use `let pi = 3.0` to shadow within a local scope.
- **`break` / `continue`** are lexically scoped to loops in the SAME function body (v2.15.1) — they cannot escape across a function call boundary.
- **All runtime errors carry source location** (v2.22.3) — `InterpreterError` is rendered rustc-style by the CLI/REPL when source is available.
- **No Python info leak via member access** (v2.18.x) — `obj.__class__`, `obj._private`, `bytes` returns are all rejected.

## Open work / where to go next

**The next strategic direction is the bytecode VM** — see [`ARCHITECTURE.md`](ARCHITECTURE.md) Phase 4. The language is feature-complete enough for a beginner-Python-equivalent surface; "optimizing how it runs" is the more interesting work than "adding more syntax." Rough plan:

1. Design a small instruction set (~30 opcodes: `LOAD_CONST`, `ADD`, `JUMP_IF_FALSE`, `CALL`, `RETURN`, etc.).
2. Compile AST → bytecode.
3. Write a stack-based VM in a single file.
4. Keep the tree-walking interpreter around as the reference implementation + for tests.
5. Reference: *Crafting Interpreters* by Bob Nystrom (Part III walks this exact path).

**Documentation work** (could go before or alongside the VM):

- **Update [`README.md`](README.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md)** to reflect the v2.25 feature surface — `let`, `finally`, slicing, format specs, the 10 new builtins, rustc-style errors, ROT-style output, info-leak hardening. The current docs lag by ~12 minor versions.
- **Revisit [`BUG_REPORT.md`](BUG_REPORT.md)** — most findings are now fixed in v2.14–v2.25, but the report still reads as if they're open. Either mark them resolved or archive the report.

**Smaller open items:**

- **Inheritance / `super`** — `super` is reserved with a clear "not supported" error since v2.25.7, but no implementation. Adding single-inheritance is a natural minor.
- **Multi-line strings** (triple-quoted).
- **Integer division `//`** — deferred in v2.25.6 because `//` is the comment marker. Could pick a different syntax (`~/`, `\\`) or change comment syntax.
- **Tab completion in the REPL** — skipped in v2.19.x as optional.
- **Closure late-binding** — `for i in [1|2|3] { funct f() { return i } append(fns, f) }` produces three closures that all see `3` (the Python footgun). Pin or fix.
- **TCO** in the interpreter for deep recursion (currently capped at Python's recursion limit and wrapped).

## Quick demo

```bash
# Run a program:
python3 -m rot examples/fizzbuzz.rot

# Validate without running:
python3 -m rot --no-run examples/factorial.rot

# REPL:
python3 -m rot

# Trace the pipeline:
python3 -m rot --trace examples/hello.rot

# Tests:
python3 -m pytest tests/   # → 628 passing
```

## TL;DR for a new session

You're picking up a learning-project programming language (ROT) at **v2.25.11**. It's a tree-walking interpreter with `let`/`finally`/slicing/f-string format specs, immutable builtins, rustc-style errors, ROT-style output, and 628 passing tests across Python 3.9–3.12 in CI. The last session was a 12-agent / 81-commit sweep that worked through the v2.13.0 audit's ~600 findings; most are fixed and pushed. The user wants action with light judgment, not constant confirmation. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the architecture, [`CHANGELOG.md`](CHANGELOG.md) for the history (newest first), and [`BUG_REPORT.md`](BUG_REPORT.md) for the audit. **The natural next direction is the bytecode VM (Phase 4 in ARCHITECTURE.md).**
