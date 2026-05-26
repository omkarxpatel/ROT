# Changelog

All notable changes to ROT are documented here. The project follows [Semantic Versioning](https://semver.org/).

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
