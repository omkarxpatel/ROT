# R.O.T

[![tests](https://github.com/omkarxpatel/ROT/actions/workflows/tests.yml/badge.svg)](https://github.com/omkarxpatel/ROT/actions/workflows/tests.yml)
[![version](https://img.shields.io/github/v/tag/omkarxpatel/ROT?label=version&sort=semver&color=blue)](https://github.com/omkarxpatel/ROT/tags)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![changelog](https://img.shields.io/badge/changelog-md-lightgrey)](CHANGELOG.md)

**R**ecursive-descent **O**ptimizing **T**ranspiler — a small custom programming language built as a learning project for understanding how languages are designed and implemented. **As of v2.0.0, `.rot` source is tokenized, parsed into a real AST, and executed directly by a tree-walking interpreter — no `exec()`, no compile-to-Python step.** The v1 transpiler-to-Python pipeline is archived in the git history (`v1.0.0` → `v1.9.0`); see [`CHANGELOG.md`](CHANGELOG.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full story.

See [`rot/__init__.py`](rot/__init__.py) for the current version and [`CHANGELOG.md`](CHANGELOG.md) for release history.

## Install

```
pip install -r requirements.txt
```

## Run

```
python -m rot examples/functions.rot
```

Default invocation parses and interprets the program silently — only the program's own output reaches stdout. Add `--trace` to see the tokenizer/parser pipeline tables. Use `--no-run` to validate without running.

## How it works (v2)

Three stages on the active pipeline:

1. **Lexer** ([rot/lexer.py](rot/lexer.py)) — hand-rolled, character-by-character. Produces `Token(lexeme, kind, line, col)`. Multi-character operators (`==`, `!=`, `<=`, `>=`) and string literals are single tokens.
2. **Parser** ([rot/syntax.py](rot/syntax.py)) — recursive-descent with Pratt parsing for expression precedence. Produces an `ast.Program` whose nodes (`FuncDef`, `IfStmt`, `Call`, `BinaryOp`, etc.) live in [rot/ast.py](rot/ast.py).
3. **Interpreter** ([rot/interpreter.py](rot/interpreter.py)) — walks the AST, maintains a lexically-scoped `Environment`, dispatches on each node. `cout` and `coutln` are built-in callables in the global env.

See [ARCHITECTURE.md](ARCHITECTURE.md) for the deep dive.

Example `.rot`:

```
funct hi(x | y) {
    if (x > y) {
        coutln(x)
    }

    elseif (x == y) {
        coutln("same")
    }

    else {
        coutln(y)
    }
}

hi(10 | 10)
```

## Roadmap

The v2 cut (AST + tree-walking interpreter, no `exec()`) shipped in [v2.0.0](CHANGELOG.md#200---2026-05-26). What's next:

- **v2.x** — bytecode + custom stack VM (~30 opcodes). Faster than tree-walking; teaches you how Python, Lua, and the JVM actually run.
- **v3.0** (?) — native codegen via LLVM IR (`llvmlite`). `rot build hello.rot` produces a real binary.

The original v1 (`.rot` → Python via `exec()`) is preserved in git history at [`v1.9.0`](https://github.com/omkarxpatel/ROT/releases/tag/v1.9.0) and earlier tags.
