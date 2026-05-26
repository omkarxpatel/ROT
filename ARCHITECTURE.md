# Architecture

A walkthrough of how `rot` is currently built (as of `v2.0.0`) and where the project is heading. This document is for anyone curious about the internals — separate from `README.md`, which is the elevator pitch.

For release-by-release history see [`CHANGELOG.md`](CHANGELOG.md). For the current version see [`rot/__init__.py`](rot/__init__.py).

---

# Part 1 — How it works today (v2.0.0)

## The pipeline at a glance

```
                          ┌──────────────────────────────────┐
                          │  examples/functions.rot          │
                          │  ───────────────────────         │
                          │  funct hi(x | y) {               │
                          │    if (x > y) { coutln(x) }      │
                          │    ...                            │
                          │  }                                │
                          └────────────────┬─────────────────┘
                                           │ read text
                                           ▼
                          ┌──────────────────────────────────┐
                          │ Lexer (rot/lexer.py)             │
                          │   hand-rolled char-by-char       │
                          └────────────────┬─────────────────┘
                                           │ list[Token]
                                           │   Token(lexeme, kind,
                                           │         line, col)
                                           ▼
                          ┌──────────────────────────────────┐
                          │ Parser (rot/syntax.py)           │
                          │   recursive-descent, Pratt expr  │
                          └────────────────┬─────────────────┘
                                           │ ast.Program
                                           │   FuncDef / IfStmt /
                                           │   ExprStmt / Call /
                                           │   BinaryOp / ...
                                           ▼
                          ┌──────────────────────────────────┐
                          │ Interpreter (rot/interpreter.py) │
                          │   tree-walking; scoped env;      │
                          │   cout/coutln as built-ins       │
                          └────────────────┬─────────────────┘
                                           │
                                           ▼
                                       program output
```

Three stages on the active path, plus the orchestrator. Python's `exec()` is no longer involved — the interpreter walks the AST directly.

(The v1.9.0 AST → Python emitter still lives in `rot/emitter.py` as a parallel/optional path, but the default compile flow goes straight through the interpreter now.)

## The modules

| Module | Job | Lines (approx) |
|---|---|---|
| [`rot/__init__.py`](rot/__init__.py) | `__version__` tag | 1 |
| [`rot/__main__.py`](rot/__main__.py) | `python -m rot` entry | 5 |
| [`rot/cli.py`](rot/cli.py) | argparse CLI surface | ~55 |
| [`rot/compiler.py`](rot/compiler.py) | orchestrates lex → parse → interpret | ~55 |
| [`rot/lexer.py`](rot/lexer.py) | hand-rolled char-by-char tokenizer | ~150 |
| [`rot/ast.py`](rot/ast.py) | AST node dataclasses | ~65 |
| [`rot/syntax.py`](rot/syntax.py) | recursive-descent parser: tokens → AST (Pratt for expressions) | ~170 |
| [`rot/interpreter.py`](rot/interpreter.py) | **tree-walking interpreter** over the AST | ~150 |
| [`rot/emitter.py`](rot/emitter.py) | AST → Python source (off the active path; kept tested) | ~80 |
| [`rot/keywords.py`](rot/keywords.py) | `KEYWORDS` lookup | ~25 |
| [`rot/token.py`](rot/token.py) | `Token` dataclass | 10 |
| [`rot/errors.py`](rot/errors.py) | `LexerError` / `ParserError` / `InterpreterError` carrying `(line, col)` | ~25 |

Total: ~800 lines of language code, ~600 lines of tests.

## Stage 1 — the Lexer

`rot/lexer.py` is a hand-rolled, character-by-character scanner (as of v1.6.0 — the original was a regex-pattern walk). At each position it dispatches on the next character — digit → scan a number; lowercase letter → scan an identifier; `"` → scan a string literal; `/` followed by `/` → scan a comment; etc. — and emits a `Token`.

Two lookups live in `rot/keywords.py`:

```python
KEYWORDS = {           # reserved-word lookup
    "cout":   "PRINT",
    "coutln": "PRINTLN",
    "funct":  "FUNCTION",
    "elseif": "ELIF",
    "if":     "IF",
    "else":   "ELSE",
}

PY_EQUIVALENT = {      # token kind → Python source (used by the transpiler)
    "PRINT":    "print",
    "PRINTLN":  "print*",   # asterisk is a marker the transpiler strips
    "FUNCTION": "def",
    "L_CURLY":  ":",        # `{` → `:`
    "R_CURLY":  "",         # `}` → nothing (Python uses indentation)
    "ELIF":     "elif",
    "COMMA":    ",",
}
```

When the scanner consumes a run of lowercase letters, it looks the lexeme up in `KEYWORDS`. If found → that's the kind (`cout` → `PRINT`). If not found → `IDENT`.

String literals are scanned as one token: `"hello world"` becomes a single `STRING_LIT` whose lexeme includes the surrounding quotes. (Pre-v1.6.0 the regex lexer broke strings into `QUOTE` / `IDENT` / `QUOTE`.)

### Example: lexing `cout("hi")`

```
position    kind         lexeme
──────────────────────────────────
  0         PRINT        'cout'
  4         L_PAREN      '('
  5         STRING_LIT   '"hi"'
  9         R_PAREN      ')'
```

### Error path

If no regex matches the current character, the lexer raises `LexerError("unexpected character '@'", line=1, col=11)`. The CLI catches and prints:

```
rot error: line 1:11: unexpected character '@'
```

## Stage 2 — the Parser (`rot/syntax.py`)

A real recursive-descent parser. Consumes the token stream, produces an `ast.Program` whose body is a list of `Statement` nodes.

Statement-level grammar (one rule per public method on the `Parser` class):

```
stmt        := func_def | if_stmt | expr_stmt
func_def    := 'funct' IDENT '(' params? ')' block
params      := IDENT ('|' IDENT)*
if_stmt     := 'if' '(' expr ')' block (elif_branch)* else_branch?
elif_branch := 'elseif' '(' expr ')' block
else_branch := 'else' block
block       := '{' stmt* '}'
expr_stmt   := expr
```

Expression-level grammar uses **Pratt parsing** with precedence levels. Higher binds tighter:

```
5  *  /                     factor
4  +  -                     term
3  <  <=  >  >=             comparison
2  ==  !=                   equality
```

All operators are left-associative. Parenthesized expressions (`(1+2)*3`) work via the `atom` rule.

> **Historical note:** v1.0.0 → v1.8.0 had a separate "transpiler" in `rot/parser.py` that walked tokens and concatenated Python strings directly — no tree, two special-case hacks (the `cout` end-kwarg insertion and `// → #` translation). It was retired in v1.9.0 once the AST + emitter could do the same job correctly.

The AST node types live in `rot/ast.py`:

```python
@dataclass class Program:     body: list[Statement]
@dataclass class ExprStmt:    expr: Expression
@dataclass class FuncDef:     name; params; body
@dataclass class IfStmt:      cond; then_block; elif_branches; else_block
@dataclass class ElifBranch:  cond; body
@dataclass class Block:       statements
@dataclass class Call:        callee; args
@dataclass class BinaryOp:    op; left; right
@dataclass class Identifier:  name
@dataclass class NumberLit:   value
@dataclass class StringLit:   value
```

## Stage 3 — the Interpreter (`rot/interpreter.py`)

Walks the AST and executes its semantics directly. No `exec()`, no intermediate Python source. The interpreter holds an `Environment` — a `dict` of name → value with a `parent` link for outer scopes — and dispatches on each AST node:

```
ExprStmt(expr)              → evaluate expr, discard result
FuncDef(name, params, body) → env.set(name, RotFunction(decl, current env))
IfStmt(cond, then, elifs,
       else)                → evaluate cond; pick branch; execute its block
Block(statements)           → execute each statement in sequence
Call(callee, args)          → evaluate callee + args; if RotFunction,
                              push a child scope and run the body;
                              if a Python callable (built-in), invoke it
BinaryOp(op, l, r)          → evaluate l and r; look op up in _BINARY_OPS
Identifier(name)            → env.get(name) — walks the parent chain
NumberLit / StringLit       → the literal value
```

`cout` and `coutln` are bound in the global environment as Python functions — the language's only built-ins so far. `cout(...)` prints with `end=""` and `sep=""`; `coutln(...)` uses the default newline.

User-defined functions are `RotFunction` instances. They close over the environment they were declared in (lexical scope). When called, they create a child environment, bind parameters, execute the body, then restore the prior environment.

Errors that aren't syntax errors come out as `InterpreterError(line, col)`: undefined names, arity mismatches, uncallable values, unknown operators.

### Why "tree-walking"?

This is the simplest interpreter architecture: literally walk the AST nodes and do what each one means. Slow per operation (every function call traverses Python objects), but the reference for what the language *means*. Future phases (bytecode VM, native codegen) optimize how it runs, not what it does.

### Emitter side-path

`rot/emitter.py` still exists. It walks the AST and produces equivalent Python source. It's not on the default execution path in v2.0.0 but its tests still pass, and a future `--transpile` flag could rewire it for diagnostics or polyglot output.

## Stage 4 — Compiler orchestration

```python
class Compiler:
    def parse(source: str) -> ast.Program:     # lex + parse → AST
    def run(source: str) -> None               # parse + interpret
```

`parse()` is exposed so `--no-run` can validate without executing; tests use it to grab the AST directly. `run()` is the full pipeline.

The CLI is thin:

```python
compiler = Compiler(trace=args.trace)
if args.no_run:
    compiler.parse(source)        # raises on syntax errors; exits clean if not
    return
compiler.run(source)              # parses + executes; raises InterpreterError on runtime issues
```

`trace=True` enables the verbose tokenizer/parser/runtime tables. Default is silent.

## The CLI surface

```
$ python -m rot examples/functions.rot              # silent parse + interpret
$ python -m rot --trace examples/functions.rot      # verbose pipeline
$ python -m rot --no-run examples/hello.rot         # parse only — validates
$ python -m rot --version                           # print version
```

## The test suite

`tests/` has five files:

- **`test_lexer.py`** — keyword vs identifier classification, line/col tracking, multi-char operator tokens, `LexerError` location, comment lexing, `R_CURLY`, uppercase rejection.
- **`test_syntax.py`** — AST construction: call shapes, atoms, Pratt precedence/associativity, parenthesized grouping, `FuncDef` / `IfStmt` / `Block`, plus a full-program parse of `examples/functions.rot`.
- **`test_interpreter.py`** — runtime semantics: `cout`/`coutln`, function definition + call, arity check, `if/elif/else` selection, arithmetic precedence, undefined-name and lexical-scope errors.
- **`test_emitter.py`** — AST → Python (off the active path but still verified): translation rules, indentation, precedence parens.
- **`test_end_to_end.py`** — every `examples/*.rot` paired with a `.expected` file. Runs through `Compiler.run()` with captured stdout.

57 tests, ~90 ms total runtime.

## Behavioral quirks worth knowing

- **Identifiers are lowercase only.** Uppercase input raises a `LexerError`. By design — keywords are lowercase, so identifiers are too.
- **`|` is the parameter separator** (not `,`). Quirky on purpose. `funct hi(x | y)` → `def hi(x,y)` in Python.
- **`{ }` blocks but indentation in output.** `{` → `:` and `}` → `""`. The user's indentation in the `.rot` source carries through to Python.
- **Multi-char operators are real tokens (since v1.7.0).** `==`, `!=`, `<=`, `>=` lex as single `EQ_EQ` / `NEQ` / `LE` / `GE` tokens. Lone `=`, `<`, `>` still produce `SETVALUE` / `LESSTHAN` / `GREATERTHAN`. `!` is only valid as part of `!=`.

---

# Part 2 — Where this is going

The current pipeline leans on Python for everything past tokenizing: there's no AST, no semantic analysis, no real execution model — `exec()` does the heavy lifting. The point of v2+ is to **own the entire pipeline**.

The roadmap below mirrors how compiler courses are taught and how real languages were built historically. Each phase is a real milestone you can demo.

## Phase 1 — hand-rolled lexer + AST ✓ (shipped across v1.6.0 → v1.9.0)

All landed:

- **v1.6.0** — Hand-rolled char-by-char lexer; AST node dataclasses; recursive-descent parser for expression-statement calls.
- **v1.7.0** — Multi-character operator tokens (`==`, `!=`, `<=`, `>=`); `BinaryOp` AST node; Pratt parsing with full precedence + associativity.
- **v1.8.0** — `Block` / `FuncDef` / `IfStmt` AST nodes and their grammar rules. The full `examples/functions.rot` now parses to an AST.
- **v1.9.0** — AST → Python emitter (`rot/emitter.py`) takes over the active compile path. The v1 transpiler is retired.

End state: source goes `Lexer → Parser (AST) → Emitter → exec`. The Python `exec()` is the only thing standing between ROT and a self-hosted runtime.

## Phase 2 — semantic analysis (next: `v1.10.0`+)

Walk the AST and resolve names. Build a scope tree. Catch:

- `cannot call non-function 'x'`
- `function 'hi' takes 2 parameters, got 1`
- `name 'foo' is not defined`

All errors carry source positions (the foundation laid in `v1.2.0` pays off here). Output looks like Rust's compiler errors — caret line under the offending token, "help:" suggestions where possible.

This is where 80% of the "real compiler feel" comes from. The language gains genuine type-checking and structural validation, even before runtime changes.

## Phase 3 — tree-walking interpreter, **drop `exec()`** ✓ (shipped in `v2.0.0`)

The headline cut. `rot/interpreter.py` walks the AST directly; `exec()` is gone. ROT no longer "compiles to Python" — it runs itself. See [Stage 3 in Part 1](#stage-3--the-interpreter-rotinterpreterpy) above.

## Phase 4 — bytecode + custom VM (planned: `v2.x`)

Design a small instruction set (~30 opcodes): `LOAD_CONST`, `ADD`, `JUMP_IF_FALSE`, `CALL`, `RETURN`, …. Compile AST → bytecode. Write a stack-based VM that runs the bytecode in one file.

Much faster than tree-walking; teaches you how Python, Lua, and the JVM actually run.

Reference: *Crafting Interpreters* by Bob Nystrom (Part III walks this exact path).

## Phase 5 — native codegen via LLVM (planned: `v3.0.0`?)

Emit LLVM IR; let LLVM produce real machine code (and real assembly). The roadmap's original "compile to assembly" goal is satisfied — you just don't hand-write it. The LLVM Python binding `llvmlite` handles the C++ side.

The end state: `rot build hello.rot` produces a native binary you can `./hello` directly. No Python in sight.

---

# Part 3 — Design decisions

A few things worth knowing if you're poking around or extending:

| Decision | Why |
|---|---|
| Lowercase-only identifiers | Mirrors keywords. Avoids the visual confusion of `IF` vs `if`. |
| `\|` as parameter separator | Distinctive. Comma is overused. Forced choice early in design; kept for character. |
| `{` `}` blocks → Python-style indentation in output | Cheap to translate; preserves the source's own indentation discipline. |
| `cout` / `coutln` | Homage to `std::cout`. Distinguishes no-newline from newline-terminated. |
| `Token` carries `(line, col)` from `v1.2.0` | Foundation for every future error path. The current code uses `(line, col)` for one error type, but every future diagnostic needs it. |
| Lexer raises `LexerError` instead of silently skipping | Bugs hide behind catch-all `except`. Make them loud early. |
| `Compiler` API split (`compile / save / execute`) | Lets tests `compile()` without writing files or executing. Lets `--no-run` exist. |
| Tests use golden `.expected` files | Refactoring toward the v2 AST without silently regressing v1 behavior is the whole point of the test suite. |

---

# Part 4 — How to find your way around

Suggested reading order if you're new to the codebase:

1. [`rot/__init__.py`](rot/__init__.py) — confirm the version.
2. [`rot/cli.py`](rot/cli.py) — see what the program does.
3. [`rot/compiler.py`](rot/compiler.py) — see how the pipeline is wired.
4. [`rot/lexer.py`](rot/lexer.py) — see how characters become tokens.
5. [`rot/keywords.py`](rot/keywords.py) — see the lookup tables.
6. [`rot/parser.py`](rot/parser.py) — see tokens become Python.
7. [`tests/`](tests/) — confirm what is and isn't guaranteed behavior.

Then run `python -m rot --trace examples/functions.rot` and watch every stage spell itself out.
