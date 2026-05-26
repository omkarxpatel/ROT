# Changelog

All notable changes to ROT are documented here. The project follows [Semantic Versioning](https://semver.org/).

## [1.6.2] - 2026-05-26

### Added
- Status badges under the README title: CI run status (live from GHA), latest semver tag, supported Python versions, and a link to `CHANGELOG.md`. All four are clickable and refresh automatically against the GitHub repo and shields.io.

## [1.6.1] - 2026-05-26

### Fixed
- CI was failing with `ModuleNotFoundError: No module named 'rot'` because the GHA workflow invokes the bare `pytest` binary, which doesn't add the project root to `sys.path` the way `python -m pytest` does. Added a minimal `pyproject.toml` with `[tool.pytest.ini_options] pythonpath = ["."]` so pytest finds the package regardless of how it's invoked.

## [1.6.0] - 2026-05-26

Phase 1 of v2 lands. None of this changes the user-facing CLI behavior — the v1 transpiler still drives the active compile path — but the architecture is now ready to grow a real AST-driven pipeline in the next phase.

### Added
- `rot/ast.py` — AST node dataclasses: `Program`, `ExprStmt`, `Call`, `Identifier`, `NumberLit`, `StringLit`. `Statement` and `Expression` type aliases for clarity.
- `rot/syntax.py:Parser` — recursive-descent parser that consumes a `Token` list and builds a `Program` AST. Phase 1 grammar covers expression-statements with function calls, identifiers, and literals (no `FuncDef` / `IfStmt` / `BinaryOp` yet — those come in v1.7+).
- `tests/test_syntax.py` — 8 tests exercising AST construction end-to-end (lex → parse → assert tree shape). Covers string-literal calls, multi-arg calls, no-arg calls, nested calls, bare identifiers, number/string atoms, and `ParserError` on truncated input.
- New lexer tests for spaced / punctuated string literals and unterminated-string error path.

### Changed
- **Lexer is now hand-rolled** (`rot/lexer.py`). The regex `TOKEN_PATTERNS` table is gone. The scanner dispatches character-by-character: digit → number, lowercase letter → identifier-or-keyword, `"` → string literal, etc. Same `Token` shape, same line/col tracking, same `LexerError` API.
- **String literals are now single tokens** (`STRING_LIT`) instead of `QUOTE` / `IDENT` / `QUOTE` triplets. Strings can now contain spaces and punctuation (`"hello, world"` lexes cleanly). The v1 transpiler handles this transparently because `STRING_LIT` falls back to its lexeme.
- `rot/keywords.py` shrunk by ~half: `TOKEN_PATTERNS` removed (dead now that the lexer is hand-rolled). Just `KEYWORDS` and `PY_EQUIVALENT` remain.
- `ARCHITECTURE.md` updated to describe v1.6.0 architecture, the new modules, and the existence of two "parsers" (the v1 transpiler in `rot/parser.py` and the real recursive-descent parser in `rot/syntax.py`).

### Removed
- `TOKEN_PATTERNS` list from `rot/keywords.py` and the `re` import / `_COMPILED_PATTERNS` cache from `rot/lexer.py`.
- The "strings aren't single tokens" behavioral quirk from `ARCHITECTURE.md`.

## [1.5.1] - 2026-05-26

### Changed
- Renamed the lexer's `[a-z]+` fallback token kind from `STRING` to `IDENT`. The old name was a vestige from v1.0.0 and conflicted with the natural meaning of "string literal" (which is what `"hello"` will be once Phase 1 of v2 adds proper string-literal tokenization). Tests and ARCHITECTURE.md updated.

## [1.5.0] - 2026-05-26

### Added
- GitHub Actions workflow `.github/workflows/tests.yml` running `pytest tests/ -v` on every push to main and every pull request, across Python 3.9 / 3.10 / 3.11 / 3.12.

## [1.4.3] - 2026-05-26

### Added
- `ARCHITECTURE.md` — detailed internals doc separate from the README. Part 1 walks the v1.4.2 pipeline (modules, lexer regex tables, the parser's `cout`/`coutln` and comment hacks, the compiler split, behavioral quirks). Part 2 lays out the v2+ roadmap phase by phase, with the cut to `2.0.0` defined as the moment `exec()` is removed.

## [1.4.2] - 2026-05-26

### Removed
- Vestigial `[A-Z]+` pattern from `TOKEN_PATTERNS`. The rot language is lowercase by design — keywords (`cout`, `funct`, …) and identifiers all match `[a-z]+`. Uppercase input now raises `LexerError` (`unexpected character 'H'`) instead of being silently classified as `STRING`. Locked in with `test_uppercase_identifiers_are_unsupported`.

## [1.4.1] - 2026-05-26

### Removed
- The `result[-5:] == "print"` defensive guard in `Parser.parse`. Tracing every realistic flow showed the condition is never reached (the lexer eats identifiers greedily, and `cout`/`coutln` always have a `(` immediately following). Added `examples/multiple_prints.rot` as a regression test exercising consecutive `cout`/`coutln` calls.

## [1.4.0] - 2026-05-26

### Added
- argparse-based CLI in `rot/cli.py` with proper `--help` output and flags:
  - `--version` — print package version and exit.
  - `--trace` — opt-in dump of the tokenizer/parser tables and execution timing (what used to print on every run).
  - `--no-run` — transpile only; write `output.py` and exit.
  - `-o / --output PATH` — choose the output path (default: `output.py`).
- `Compiler.compile() / .save() / .execute()` — pipeline split into three reusable methods.
- `Lexer(trace=...)` and `Parser(trace=...)` accept a flag so debug prints are gated cleanly at the right layer.

### Changed
- **Default `python -m rot <file>` is now silent** except for the program's own output. Verbose pipeline traces are opt-in via `--trace`.
- End-to-end test uses `Compiler.compile()` directly. Unit tests dropped their `contextlib.redirect_stdout` wrappers since lexer/parser are silent by default now.

### Removed
- `os.system("clear")` at the start of every run. Hostile to scrollback and shell-specific.
- `Compiler.run()` convenience method (no callers; `compile + save + execute` is explicit at the CLI).

## [1.3.0] - 2026-05-26

### Added
- `tests/test_lexer.py`, `tests/test_parser.py`, `tests/test_end_to_end.py` — first real pytest suite. Lexer/parser unit tests cover keyword vs identifier classification, line/col tracking, `LexerError` location, comment lexing, and `R_CURLY` emission. End-to-end tests are parametrized over every `examples/*.rot` file with a sibling `.expected`.
- `examples/hello.rot` + `.expected` and `examples/functions.expected` — golden outputs for the test suite.
- `requirements-dev.txt` (currently just `pytest`).

### Changed
- Moved the historical scratch from `tests/init/` and `tests/other/` into `scratch/` so `tests/` is purely test code now.
- `.gitignore` now also ignores `.pytest_cache/`.

## [1.2.2] - 2026-05-26

### Changed
- README trimmed: removed the `## Layout` section and the hardcoded version pointer. Version and history now live in `rot/__init__.py` and `CHANGELOG.md` respectively (single source of truth).

## [1.2.1] - 2026-05-26

### Added
- Backfilled the historical `[1.0.0]` entry to this changelog.

## [1.2.0] - 2026-05-26

### Added
- `rot/token.py` with a `Token` dataclass carrying `(lexeme, kind, line, col)`. Tokens now know where they came from — foundation for real diagnostics.
- `rot/errors.py` with `RotError`, `LexerError`, and `ParserError`. All exceptions carry `(line, col)` and pretty-print via the CLI.
- The lexer now raises `LexerError` on an unrecognized character with the exact source position (was silently skipped before).

### Changed
- **Keyword tables consolidated into one source of truth** in `rot/keywords.py`:
  - `KEYWORDS` — reserved-word lookup (`cout → PRINT`, …).
  - `TOKEN_PATTERNS` — single ordered list of `(regex, kind)` tried in order; `kind=None` means "identifier or keyword (look up in `KEYWORDS`)".
  - `PY_EQUIVALENT` — token kind → Python equivalent for the parser.
- Lexer no longer does the two-hop `LOOKUP_KEYWORD → KEYWORD_TYPES` dance or the "is this STRING actually a keyword" re-lookup hack — keyword resolution is explicit.
- Compiled regexes are cached at module load (were being recompiled every character).
- CLI now catches `RotError` and prints `rot error: line N:M: ...` instead of letting tracebacks leak.

### Fixed
- `//` comments now correctly translate to Python (`// foo` → `# foo`). Previously the parser's `DOUBLE_CHECKING` branch was order-reversed and effectively broken; comment detection has moved to the lexer where it belongs.
- `}` is now a real token (`R_CURLY`) that maps to the empty string in the Python output. Previously it was silently dropped by the catch-all `except Exception: pass` in the lexer.

### Removed
- `LOOKUP_KEYWORD`, `KEYWORD_TYPES`, `ANTI_KEYWORD`, `SYNTAX_TREE`, `DOUBLE_CHECKING` — replaced by the three tables above. `SYNTAX_TREE` was dead code.
- Bare `except Exception: pass` blocks in the lexer/parser.
- Dead `idx` local in the parser.

## [1.1.0] - 2026-05-26

### Added
- `rot/` Python package layout with submodules: `lexer`, `parser`, `compiler`, `cli`, `keywords`, plus `__main__.py` for `python -m rot`.
- `__version__` tag in `rot/__init__.py`.
- `.gitignore` for build artifacts (`output.py`, `__pycache__/`, `.venv/`).

### Changed
- Flattened repository layout: removed the `Version 1/` folder. Examples now live in `examples/`, tests in `tests/`, requirements at repo root.
- Monolithic `Lexer` god-class split into `Lexer` (tokenizing), `Parser` (token → Python), and `Compiler` (orchestration).

### Removed
- Duplicate `VERSION1.md` (root `README.md` is canonical).
- Duplicate `tests/example.rot` (identical to `examples/functions.rot`).
- Generated `output.py` checked into git (now built on demand and gitignored).

## [1.0.0] - 2024-01-24

The original. Living in a `Version 1/` folder, no package, no version tag — `python3 main.py main.rot` and the language ran.

### Added
- The `.rot` language surface: `cout` / `coutln`, `funct`, `if` / `elseif` / `else`, `{ }` blocks, `|` as the parameter separator, arithmetic and comparison operators.
- Three-stage pipeline in a single `main.py`:
  1. **Tokenizer** — regex-based, driven by a `lookupKeyword` hashmap that mapped each source character/word to a regex pattern.
  2. **Parser** — walked tokens, looked each kind up in an `antiKeyword` table, concatenated the Python equivalents into a string.
  3. **Execution** — wrote the resulting Python to `output.py` and ran it via Python's built-in `exec()`.
- Verbose colorized trace of every stage via `colorama`.
- `tests/example.rot` and `main.rot` (identical) demonstrating functions, conditionals, and the `cout` / `coutln` distinction.

### Known issues (carried into v1.1.0, addressed in v1.2.0)
- Bare `except Exception: pass` around every stage silently swallowed unrecognized characters.
- `lookupKeyword` and `keywordTypes` encoded the same information twice in opposite directions; the lexer needed a "re-lookup the STRING I just matched" hack to tell identifiers from reserved words.
- `//` comment handling was order-reversed and effectively broken.
- `}` had no token at all — silently dropped by the catch-all `except`.
