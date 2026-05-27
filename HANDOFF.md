# HANDOFF — Session context for ROT

A snapshot of project state and conventions for a new Claude session picking up where the last one left off. For deeper detail, see [`README.md`](README.md), [`ARCHITECTURE.md`](ARCHITECTURE.md), and [`CHANGELOG.md`](CHANGELOG.md).

## What ROT is

A custom programming language built as a learning project and portfolio piece.

- **Surface:** C++/Python-flavored hybrid. `funct` for `def`, `cout` / `coutln` for `print`, `|` as parameter/arg separator, C-style braces.
- **Pipeline:** source → hand-rolled char-by-char lexer → recursive-descent parser (Pratt for expressions) → AST → tree-walking interpreter. Python `exec()` has been gone since v2.0.0.
- **Current version:** see [`rot/__init__.py`](rot/__init__.py). At the time of writing: `2.13.0`.
- **GitHub:** https://github.com/omkarxpatel/ROT
- **CI:** GitHub Actions running `pytest` across Python 3.9 / 3.10 / 3.11 / 3.12.

## Project layout

```
rot/                    # the language package
├── __init__.py         #   __version__
├── __main__.py         #   `python -m rot` entry
├── cli.py              #   argparse CLI; default starts REPL if no file
├── compiler.py         #   orchestrates lex → parse → interpret
├── lexer.py            #   hand-rolled char-by-char tokenizer
├── token.py            #   Token dataclass (lexeme, kind, line, col)
├── keywords.py         #   KEYWORDS dict
├── ast.py              #   AST node dataclasses (Program, FuncDef, IfStmt, ListLit, ClassDef, ...)
├── syntax.py           #   recursive-descent parser; Pratt for expressions
├── interpreter.py      #   tree-walking interpreter + Environment + RotClass/Instance/BoundMethod
├── builtins.py         #   standard library (cout, len, math, file I/O, type, random, ...)
├── emitter.py          #   AST → Python source — OFF the active path, kept tested for parity
├── repl.py             #   interactive REPL with multi-line input + history
└── errors.py           #   RotError / LexerError / ParserError / InterpreterError
tests/                  # 201 tests, pytest. Golden-file end-to-end + unit tests per module.
examples/               # 8 working .rot programs with .expected golden outputs
ARCHITECTURE.md         # deep design doc
CHANGELOG.md            # per-release notes (read newest first)
README.md               # short overview + badges
pyproject.toml          # pytest pythonpath config (so `pytest` binary finds the package)
.github/workflows/      # GHA CI workflow
```

## What ROT can do (as of v2.13.0)

The language progressed from a regex-based Python transpiler (v1.0.0) to a feature-complete tree-walking interpreter with:

- Variables, compound assignment (`+= -= *= /= %=`)
- Numbers (int + float), strings (with escapes), booleans (`true` / `false`), `null`
- Arithmetic, comparison, logical (`and` / `or` / `not`), modulo, unary `-`
- Conditionals (`if` / `elseif` / `else`)
- Loops (`while`, `for x in iter`), `break`, `continue`
- Functions (`funct`), return values, recursion, **closures that mutate enclosing scope** (intentional v2.10.0 design)
- Classes (`class`, `this`, `init`, methods, fields, instances)
- Lists `[a | b | c]`, indexing, mutation, iteration
- Dicts `{k: v | k2: v2}`, member access `obj.attr` (also exposes Python str/list/dict methods for free)
- Error handling: `try` / `catch` / `throw` (catches both user `throw`s and any `InterpreterError`)
- String interpolation: `f"hello, {name}"`
- Module system: `import "path"` (relative to importing file, cached, prevents circular loops)
- Interactive REPL (`python -m rot` with no file)
- ~25 builtins: `cout`, `coutln`, `str`, `num`, `len`, `range`, `input`, `read_file`, `write_file`, `abs`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `round`, `pi`, `e`, `type`, `is_num`/`is_str`/`is_list`/`is_dict`/`is_bool`/`is_null`/`is_func`, `rand_int`, `rand_float`, `assert`, `append`, `pop`.

## Recent session: what happened

### 1. v2.3.0 → v2.12.0 — Autonomous 10-release language build

User asked: *"implement every feature a modern general-purpose language would have."* I worked through 10 minor releases adding everything in the list above. Tests grew from 25 to 181. All committed and pushed.

### 2. v2.13.0 — Bug-fix sweep from external code review

An external review agent generated a 30+ item bug report. Triage:

- **14 confirmed bugs fixed** — all in v2.13.0:
  - Top-level `break` / `continue` / `return` now raise `InterpreterError` instead of escaping as `BaseException` with a Python traceback. Tracked via `Interpreter._loop_depth` / `_function_depth`.
  - Python exceptions (`ZeroDivisionError`, `TypeError`, `IndexError`, `OSError`, etc.) wrapped as `InterpreterError` — now catchable in rot's own `try` / `catch`.
  - **Method scoping bug** (real impact): `BoundMethod.call` was using `local.set(param, value)` after v2.10.0's chain-walking `set`. Method params with the same name as an outer variable would *silently mutate the outer*. Same bug for `this`. Both fixed by switching to `set_local`.
  - CRLF (`\r\n`) handling, f-string trailing-token validation (`f"{1 2}"` now errors), member access for keyword names (`obj.class`), dropped vestigial `SINGLE_QUOTE` token.
- **6 design decisions reaffirmed**, not bugs:
  - `Environment.set` walking the parent chain *is* the v2.10.0 closure-mutation feature.
  - For-loop var always binding locally is intentional (uses `set_local`).
- **4 deferred as known limitations**: emitter drift (emitter is off the active compile path), f-string nested braces, multi-line string semantics, unknown-escape behavior.

> **Caveat:** the same review agent later re-ran from its own worktree branch (`agents/rot-codebase-bug-analysis-report` at `47f20d0`) and reported "nothing fixed." That's a false negative — the worktree branch diverged before v2.13.0. The fixes are on `main` at `cbd707e`. If the agent re-runs, point it at the main repo or merge `origin/main` into its branch first.

## User conventions / preferences

The user (Omkar) is the project owner. Things to know:

- **Bump the version on every code change.** Patch for bug-fixes/docs, minor for new features, major for breaking changes. Every commit gets a matching git tag (`v2.13.0` etc.). Always push tags.
- **Commit per change.** Don't batch unrelated changes. `CHANGELOG.md` gets updated alongside each bump.
- **Action-oriented.** "okay" or "go" means "execute the plan." Doesn't want constant confirmation; if it's clearly the right next step, just do it. If a real design question comes up, ask.
- **Style preference:** concise prose, structured tables, real code examples over abstractions.
- **Tooling preference:** avoid over-engineering. Flat `rot/` package (no `src/`), `pyproject.toml` only added when pytest forced it, no module system until v2.11.0, etc.
- **No emojis in files** unless requested (per global `CLAUDE.md`).

## Repo conventions

- `funct` not `def`, `cout` / `coutln` not `print`, `|` not `,` for arg/param separator, `this` not `self`, C-style braces.
- Identifiers: `[A-Za-z_][A-Za-z_0-9]*` (lifted from lowercase-only in v2.6.0 when classes landed).
- Output style: `cout` / `coutln` print rot-style — `null` not `None`, `true` / `false` not `True` / `False`. Same for `str()` builtin.
- **Closures can mutate enclosing scope** (chain-walking `set` in `Environment`). To shadow, use a different name or a function parameter.
- **Method params and `this` use `set_local`** (don't walk chain). Same for for-loop iteration variable.

## Open work / where to go next

**The next strategic direction is the bytecode VM** — see [`ARCHITECTURE.md`](ARCHITECTURE.md) Phase 4. The language is feature-complete enough that "optimizing how it runs" is the more interesting work than "adding more syntax." Rough plan:

1. Design a small instruction set (~30 opcodes: `LOAD_CONST`, `ADD`, `JUMP_IF_FALSE`, `CALL`, `RETURN`, etc.).
2. Compile AST → bytecode.
3. Write a stack-based VM in a single file.
4. Keep the tree-walking interpreter around as the reference implementation + for tests.
5. Reference: *Crafting Interpreters* by Bob Nystrom (Part III walks this exact path).

**Smaller open items** if the VM work feels too big to start:

- **Emitter drift** — the emitter still has known incorrect translations for `this` / `+`-coercion / `throw` / `import`. Could either fix or remove the emitter.
- **`--transpile` flag** to re-expose the emitter as a separate operation.
- **Inheritance / `super`** — only single classes currently work.
- **`nonlocal` / `global` keywords** — current chain-walk `set` is the workaround.
- **Multi-line strings** (triple-quoted).
- **Better error formatting** — rustc-style source-line + caret rendering using the `(line, col)` we already capture.
- **Tail-call optimization** in the interpreter (for deep recursion).

## Quick demo

```bash
# Run a program:
python -m rot examples/fizzbuzz.rot

# Validate without running:
python -m rot --no-run examples/factorial.rot

# REPL:
python -m rot

# Trace the pipeline:
python -m rot --trace examples/hello.rot

# Tests:
python -m pytest tests/   # → 201 passing
```

## TL;DR for a new session

You're picking up a learning-project programming language (ROT) at v2.13.0. It's a tree-walking interpreter with all the basics of a beginner-Python-equivalent language: classes, lists, dicts, try/catch, modules, REPL. 201 tests pass, CI green. The user wants action with light judgment, not constant confirmation. Read [`ARCHITECTURE.md`](ARCHITECTURE.md) for the architecture and [`CHANGELOG.md`](CHANGELOG.md) for the history. The natural next direction is the bytecode VM.
