# ROT

[![tests](https://github.com/omkarxpatel/ROT/actions/workflows/tests.yml/badge.svg)](https://github.com/omkarxpatel/ROT/actions/workflows/tests.yml)
[![version](https://img.shields.io/github/v/tag/omkarxpatel/ROT?label=version&sort=semver&color=blue)](https://github.com/omkarxpatel/ROT/tags)
[![python](https://img.shields.io/badge/python-3.9%20%7C%203.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![changelog](https://img.shields.io/badge/changelog-md-lightgrey)](CHANGELOG.md)

**R**eflexive **O**perational **T**ransducer — a small custom programming language built as a learning project for understanding how languages are designed and implemented. The current version is a Python-based transpiler — `.rot` source is tokenized, parsed against a keyword table, transformed into equivalent Python, and executed via `exec()`. Future versions replace `exec()` with a real interpreter, then a bytecode VM, then native codegen (see "Roadmap" below).

See [`rot/__init__.py`](rot/__init__.py) for the current version and [`CHANGELOG.md`](CHANGELOG.md) for release history.

## Install

```
pip install -r requirements.txt
```

## Run

```
python -m rot examples/functions.rot
```

The compiler prints the tokenizer table, the parser transformation, writes the generated Python to `output.py`, and runs it.

## How it works (v1)

Three stages, all driven by the keyword tables in [rot/keywords.py](rot/keywords.py):

1. **Tokenizer** ([rot/lexer.py](rot/lexer.py)) — walks the source character-by-character, matches each chunk against a regex from the lookup table, and emits `[lexeme, token_type]` pairs. For example, `cout("hello")` becomes:

    ```
    0    |  'cout'    |  PRINT
    1    |  '('       |  L_PAREN
    2    |  '"'       |  QUOTE
    3    |  'hello'   |  STRING
    4    |  '"'       |  QUOTE
    5    |  ')'       |  R_PAREN
    ```

2. **Parser** ([rot/parser.py](rot/parser.py)) — maps each token type to its Python equivalent via the `ANTI_KEYWORD` table (`PRINT → print`, `FUNCTION → def`, `L_CURLY → :`, etc.) and concatenates the result.

3. **Execution** ([rot/compiler.py](rot/compiler.py)) — writes the Python output to `output.py` and runs it through the built-in `exec()`.

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

v1 leans on Python for nearly everything past the parser. The point of subsequent versions is to own the full pipeline:

- **v2** — hand-rolled lexer + recursive-descent parser → proper AST, semantic analysis with real error diagnostics, tree-walking interpreter (no more `exec()`).
- **v3** — bytecode + custom stack VM.
- **v4** — native codegen via LLVM IR.
