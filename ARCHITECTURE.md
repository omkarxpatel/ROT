# Architecture

A walkthrough of how `rot` is currently built (as of `v1.6.0`) and where the project is heading. This document is for anyone curious about the internals — separate from `README.md`, which is the elevator pitch.

For release-by-release history see [`CHANGELOG.md`](CHANGELOG.md). For the current version see [`rot/__init__.py`](rot/__init__.py).

---

# Part 1 — How it works today (v1.6.0)

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
                          │   regex pattern walk             │
                          └────────────────┬─────────────────┘
                                           │ list[Token]
                                           │   Token(lexeme, kind,
                                           │         line, col)
                                           ▼
                          ┌──────────────────────────────────┐
                          │ Parser (rot/parser.py)           │
                          │   token → Python translator      │
                          └────────────────┬─────────────────┘
                                           │ python source (str)
                                           ▼
                          ┌──────────────────────────────────┐
                          │ Compiler.save → output.py        │
                          │ Compiler.execute → exec()        │
                          └────────────────┬─────────────────┘
                                           │
                                           ▼
                                       program output
```

Three stages, plus the orchestrator. The `Compiler` ties them together; the CLI ties the compiler to the user.

## The modules

| Module | Job | Lines (approx) |
|---|---|---|
| [`rot/__init__.py`](rot/__init__.py) | `__version__` tag | 1 |
| [`rot/__main__.py`](rot/__main__.py) | `python -m rot` entry | 5 |
| [`rot/cli.py`](rot/cli.py) | argparse CLI surface | ~60 |
| [`rot/compiler.py`](rot/compiler.py) | orchestrates lex → parse → exec | ~55 |
| [`rot/lexer.py`](rot/lexer.py) | hand-rolled char-by-char tokenizer | ~120 |
| [`rot/parser.py`](rot/parser.py) | tokens → Python source string (the transpiler) | ~70 |
| [`rot/ast.py`](rot/ast.py) | AST node dataclasses | ~40 |
| [`rot/syntax.py`](rot/syntax.py) | recursive-descent parser: tokens → AST | ~100 |
| [`rot/keywords.py`](rot/keywords.py) | `KEYWORDS` + `PY_EQUIVALENT` lookups | ~30 |
| [`rot/token.py`](rot/token.py) | `Token` dataclass | 10 |
| [`rot/errors.py`](rot/errors.py) | `LexerError` / `ParserError` carrying `(line, col)` | ~20 |

Total: ~500 lines of language code, ~250 lines of tests.

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

## Stage 2 — the Transpiler (`rot/parser.py`)

Misleading name: the class is called `Parser` for historical reasons but doesn't actually *parse* in the linguistic sense. It builds no tree. It's a token-to-Python-source translator.

(As of v1.6.0 there's a **real** recursive-descent parser in `rot/syntax.py` that builds an AST — see [Stage 2.5](#stage-25--the-ast-builder-new-in-v160). The transpiler is still on the active compile path while the AST is being developed; the two coexist.)

```python
for i, token in enumerate(tokens):
    parsed = PY_EQUIVALENT.get(token.kind, token.lexeme)
    # ... two special cases (see below) ...
    result += parsed
return result
```

When `kind` is in `PY_EQUIVALENT`, the Python equivalent is appended. Otherwise the raw lexeme is appended. `cout` → `print`, `funct` → `def`, `L_CURLY` (`{`) → `:`, etc.

Two special cases live in the parser:

### Special case 1: `cout` no-newline insertion

`cout(...)` should print without a newline (matching `std::cout`). `coutln(...)` should print *with* a newline (Python's default). The trick:

- `cout` → `print` (kind `PRINT`)
- `coutln` → `print*` (kind `PRINTLN`, asterisk is a sentinel)

When the parser sees `print` (from `cout`), it scans forward through the token list counting parens, finds the matching `)`, and **inserts** a synthetic `, end=""` token before it. When it sees `print*` (from `coutln`), it strips the asterisk.

End result:
- `cout("hi")` → `print("hi", end="")`
- `coutln("hi")` → `print("hi")`

### Special case 2: COMMENT translation

`COMMENT` tokens have lexemes like `// foo`. The parser emits `"# " + lexeme[2:]` so `// foo` becomes `#  foo` (the leading slash-pair is replaced; the space after is the user's).

## Stage 2.5 — the AST builder (new in v1.6.0)

`rot/ast.py` defines the AST node types as dataclasses:

```python
Program(body: list[Statement])
ExprStmt(expr: Expression)
Call(callee: Expression, args: list[Expression])
Identifier(name: str)
NumberLit(value: int)
StringLit(value: str)
```

`rot/syntax.py:Parser` consumes the token stream and builds a `Program` via recursive descent. Phase 1 grammar:

```
program     := stmt*
stmt        := expr_stmt
expr_stmt   := expr
expr        := call | atom
call        := callable '(' args ')'
args        := ( expr ('|' expr)* )?
callable    := IDENT | 'cout' | 'coutln'
atom        := callable | NUMBER | STRING_LIT
```

Whitespace, newlines, and comments are stripped before parsing — Phase 1 doesn't care about source layout.

The AST is **not yet on the active compile path** — `Compiler.compile()` still uses the transpiler (`rot/parser.py`) to go straight from tokens to Python. The AST is exercised by `tests/test_syntax.py` and is ready to become primary in Phase 2 (semantic analysis) and Phase 3 (the tree-walking interpreter that drops `exec()`).

## Stage 3 — Compiler orchestration

```python
class Compiler:
    def compile(source: str) -> str:           # lex + parse, return Python string
    def save(python_code: str, path: str) -> None
    def execute(python_code: str) -> None      # exec() the generated Python
```

The split lets the CLI offer `--no-run` (transpile only) and tests skip `save()` and use `exec()` with a captured stdout.

The CLI assembles them based on flags:

```python
compiler = Compiler(trace=args.trace)
python_code = compiler.compile(source)
compiler.save(python_code, args.output)
if not args.no_run:
    compiler.execute(python_code)
```

`trace=True` enables the verbose pipeline tables (the colored boxes the old version printed unconditionally). Default is silent.

## The CLI surface

```
$ python -m rot examples/functions.rot              # silent compile + run
$ python -m rot --trace examples/functions.rot      # verbose pipeline
$ python -m rot --no-run examples/hello.rot         # transpile only
$ python -m rot -o build.py examples/hello.rot      # custom output path
$ python -m rot --version                           # print version
```

## The test suite

`tests/` has three files:

- **`test_lexer.py`** — keyword vs identifier classification, line/col tracking, `LexerError` location, comment lexing, `R_CURLY`, uppercase rejection.
- **`test_parser.py`** — `cout` vs `coutln` translation, function-def shape, fallback-to-lexeme behavior, empty-emission for `}`.
- **`test_end_to_end.py`** — every `examples/*.rot` paired with a `.expected` file. Runs through `Compiler.compile()`, `exec`s the result, asserts stdout matches.

15 tests, ~30 ms total runtime.

## Behavioral quirks worth knowing

- **Identifiers are lowercase only.** Uppercase input raises a `LexerError`. By design — keywords are lowercase, so identifiers are too.
- **`|` is the parameter separator** (not `,`). Quirky on purpose. `funct hi(x | y)` → `def hi(x,y)` in Python.
- **`{ }` blocks but indentation in output.** `{` → `:` and `}` → `""`. The user's indentation in the `.rot` source carries through to Python.
- **`==` works by accident.** Two `=` tokens emit `=` each, so the output has `==`. There's no `EqualEqual` token. (A future v1.7+ change will introduce real multi-character operator tokens.)

---

# Part 2 — Where this is going

The current pipeline leans on Python for everything past tokenizing: there's no AST, no semantic analysis, no real execution model — `exec()` does the heavy lifting. The point of v2+ is to **own the entire pipeline**.

The roadmap below mirrors how compiler courses are taught and how real languages were built historically. Each phase is a real milestone you can demo.

## Phase 1 — hand-rolled lexer + AST ✓ (shipped in `v1.6.0`)

Two things landed:

- **Hand-rolled lexer** in `rot/lexer.py` — no regex involvement at all. Same `Token` output as before, with one upgrade: `"hello world"` is a single `STRING_LIT` token, so strings can contain arbitrary content.
- **AST + recursive-descent parser** — `rot/ast.py` defines the node dataclasses; `rot/syntax.py:Parser` builds a `Program` from a token list. See [Stage 2.5](#stage-25--the-ast-builder-new-in-v160) above for details.

Still pending for later in v1.x:
- `FuncDef`, `IfStmt`, `BinaryOp` nodes + grammar rules to populate them.
- Multi-character operator tokens (`==`, `<=`, `>=`, `!=`) replacing the current "two `=`s by accident" trick.
- Pratt parsing for expression precedence once arithmetic / comparison operators are real tokens.

## Phase 2 — semantic analysis (planned: `v1.7.0`)

Walk the AST and resolve names. Build a scope tree. Catch:

- `cannot call non-function 'x'`
- `function 'hi' takes 2 parameters, got 1`
- `name 'foo' is not defined`

All errors carry source positions (the foundation laid in `v1.2.0` pays off here). Output looks like Rust's compiler errors — caret line under the offending token, "help:" suggestions where possible.

This is where 80% of the "real compiler feel" comes from. The language gains genuine type-checking and structural validation, even before runtime changes.

## Phase 3 — tree-walking interpreter, **drop `exec()`** (`v2.0.0`)

The headline change. Instead of generating Python source and calling `exec()`, walk the AST directly and execute its semantics:

```python
class Interpreter:
    def visit_NumberLit(self, node):  return node.value
    def visit_BinaryOp(self, node):
        l, r = self.visit(node.left), self.visit(node.right)
        return {"+": l + r, "-": l - r, ">": l > r, ...}[node.op]
    def visit_Call(self, node):  ...
```

Slow but correct. This is the reference implementation forever; future phases optimize what it does, not what it means.

This is the cut to **`2.0.0`** — `exec()` going away is the defining v1-vs-v2 boundary. Once it's gone, ROT no longer "compiles to Python." It compiles itself.

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
