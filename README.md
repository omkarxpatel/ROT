# R.O.T

[![tests](https://github.com/omkarxpatel/ROT/actions/workflows/tests.yml/badge.svg)](https://github.com/omkarxpatel/ROT/actions/workflows/tests.yml)
[![version](https://img.shields.io/github/v/tag/omkarxpatel/ROT?label=version&sort=semver&color=blue)](https://github.com/omkarxpatel/ROT/tags)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![changelog](https://img.shields.io/badge/changelog-md-lightgrey)](CHANGELOG.md)

**R**ecursive-descent **O**ptimizing **T**ranspiler — a small custom programming language built as a learning project + portfolio piece. ROT is C++/Python-flavored: `funct` instead of `def`, `cout`/`coutln` instead of `print`, `|` instead of `,` for arg separators, `this` instead of `self`, `//` for comments, C-style braces. Since v2.0.0 the source is tokenized, parsed into a real AST, and executed by a tree-walking interpreter — no `exec()`, no compile-to-Python.

See [`rot/__init__.py`](rot/__init__.py) for the current version and [`CHANGELOG.md`](CHANGELOG.md) for the full release history (newest first).

## Try it

```bash
pip install -r requirements.txt
python -m rot examples/fizzbuzz.rot      # run a program
python -m rot                            # REPL
python -m rot --no-run file.rot          # validate without running
python -m rot --trace file.rot           # show the lex / parse / interpret stages
```

There's also a browser playground that runs ROT entirely client-side via [Pyodide](https://pyodide.org/). See [`web/`](web/) for the Next.js site (landing page, docs, playground, paper PDF).

## Taste

```
// recursive: factorial
funct fact(n) {
    if (n <= 1) { return 1 }
    return n * fact(n - 1)
}
coutln(fact(10))                              // 3628800

// classes
class Counter {
    init() { this.n = 0 }
    tick() { this.n += 1 }
    show() { coutln(f"count = {this.n}") }
}

c = Counter()
for i in range(3) { c.tick() }
c.show()                                      // count = 3

// error handling with finally
try {
    throw "boom"
} catch (e) {
    coutln(f"caught: {e}")
} finally {
    coutln("cleanup")
}
```

See [`examples/`](examples/) for full programs (counter, factorial, fizzbuzz, functions, hello, multiple_prints, sum_list).

## Highlights

| Feature | Notes |
|---|---|
| **`let` keyword** | Opt-in fresh-local binding. Bare `x = 1` chain-walks per the v2.10.0 closure-mutation design; `let x = 1` always creates a fresh local. |
| **`try` / `catch` / `finally`** | Full error handling. `finally` runs through `return`/`break`/`continue`/`throw`. |
| **Slicing** | `s[a:b:c]` for strings and lists. Negative bounds wrap; reverse with `[::-1]`. |
| **f-string format specs** | `f"{pi:.2f}"`, `f"{n:>5}"` — Python-compatible spec syntax. |
| **rustc-style errors** | Source line + caret + Python-ism hints (`print` → "did you mean 'cout'?"). |
| **Immutable builtins** | `pi = 3.0` is rejected. Shadow locally with `let pi = 3.0`. |
| **Info-leak hardening** | No `obj.__class__`, no `__bases__`, no `bytes` returns from Python passthrough. |
| **35+ builtins** | `cout`, `coutln`, `str`, `num`, `len`, `range`, `read_file`, `write_file`, `sum`, `sorted`, `reversed`, `keys`, `values`, `items`, `chr`, `ord`, `seed`, `exit`, and the rest. |

## How it works

Three stages on the active pipeline:

1. **Lexer** ([rot/lexer.py](rot/lexer.py)) — hand-rolled, character-by-character. Produces `Token(lexeme, kind, line, col)`. Multi-character operators, string literals, and f-strings are single tokens.
2. **Parser** ([rot/syntax.py](rot/syntax.py)) — recursive-descent with Pratt parsing for expression precedence. Produces `ast.Program`; every AST node carries `line`/`col` source positions.
3. **Interpreter** ([rot/interpreter.py](rot/interpreter.py)) — walks the AST, maintains a chain-walking `Environment` (with a frozen builtins layer at the root), dispatches each node. Runtime errors carry the source position threaded via a `_locate` dispatcher wrapper; the CLI renders them rustc-style.

The standalone Python-source emitter that lived in `rot/emitter.py` was removed in v2.23.0 once it had drifted too far from interpreter semantics. The tree-walking interpreter is the only reference implementation.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the deep dive and [paper/main.pdf](paper/main.pdf) for the design retrospective.

## Repo layout

```
rot/                  the language package (~3,800 LOC across lexer / syntax / interpreter / builtins / repl)
tests/                628 tests across per-layer, end-to-end, CLI, REPL, compiler
examples/             7 working .rot programs paired with .expected golden outputs
paper/                10-page LaTeX design retrospective (compiled main.pdf included)
web/                  Next.js 15 + Pyodide site: landing / docs / playground / paper PDF
ARCHITECTURE.md       deep architecture doc
CHANGELOG.md          per-release notes
HANDOFF.md            session-to-session snapshot
BUG_REPORT.md         v2.13.0 exhaustive audit (most findings fixed across v2.14 → v2.25)
```

## Tests

```bash
python -m pytest tests/                  # 628 passing
```

CI runs on Python 3.9 / 3.10 / 3.11 / 3.12 via GitHub Actions ([workflow](.github/workflows/tests.yml)).

## Roadmap

The v2.x cut took the language from "regex transpiler" (v1.0.0) to a feature-complete tree-walking interpreter (v2.25.15) with `let`, `finally`, slicing, f-string format specs, rustc-style errors, and 628 tests.

- **v2.x — bytecode VM**. A small stack-based VM with ~30 opcodes (Phase 4 in [ARCHITECTURE.md](ARCHITECTURE.md)). The tree-walking interpreter stays as the reference; bytecode is the fast path. Following *Crafting Interpreters* Part III as the rough guide.
- **v3.0 (?) — native codegen**. LLVM IR via `llvmlite`. `rot build hello.rot` produces a binary.

The original v1 (`.rot` → Python via `exec()`) is preserved in git history at [`v1.9.0`](https://github.com/omkarxpatel/ROT/releases/tag/v1.9.0) and earlier tags.
