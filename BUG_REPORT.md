# ROT v2.13.0 — Exhaustive Bug Report

Comprehensive audit of the ROT codebase. Findings produced by seven parallel analysis passes (lexer, parser, interpreter, builtins, emitter, CLI/REPL/compiler, test-coverage). Each finding carries a stable ID (`L*`, `P*`, `I*`, `B*`, `E*`, `T*`, `C*`) so it can be referenced individually.

Counts: 66 lexer · 160 parser · 82 interpreter · 87 builtins · 40 emitter (+1 AST hole) · 122 test-coverage · 50 CLI/REPL/compiler/errors. **≈ 600 numbered findings.**

---

## Table of contents

1. [Executive summary](#executive-summary)
2. [Top cross-cutting themes](#top-cross-cutting-themes)
3. [Recommended fix order](#recommended-fix-order)
4. [Lexer findings (L1–L66)](#lexer-findings)
5. [Parser findings (P1–P160)](#parser-findings)
6. [Interpreter findings (I1–I82)](#interpreter-findings)
7. [Builtins findings (B1–B87)](#builtins-findings)
8. [Emitter findings (E1–E40)](#emitter-findings)
9. [CLI / REPL / Compiler / Errors findings (C1–C50)](#cli--repl--compiler--errors-findings)
10. [Test coverage gaps (T1–T122)](#test-coverage-gaps)

---

## Executive summary

**Severity tally (cross-layer):**

| Class | Count | Examples |
|---|---|---|
| Crash / Python traceback leak | ~30 | C1 PermissionError, C5 uncaught throw, I10 RecursionError, E12 builtins NameError |
| Wrong output (silent miscompute) | ~20 | E13 `assert` becomes tuple, E1/E2 `null`/`true` print as Python, B41 wrong `pop` message |
| Logical / scoping bug | ~25 | I1 `break` across function boundary, I12 catch-var leak, I15 nested funct clobbers outer, L1 lexer state not reset |
| Error quality (Python phrasing leaks) | ~40 | I27, B4-B9, B20, C20 InterpreterError has no line/col |
| Missing feature gap | ~30 | I43 no `finally`, I33 no slicing, P6 no `else if`, B47 no seed |
| Test coverage gaps | 122 | see T1-T122 |
| Emitter drift | 40 | see E1-E40 |
| Suspect / fragility | ~50 | env chain-walk + `set_local` interactions |

**Highest-impact findings (must-fix):**

1. **[I1] / [I2]** — `break` and `continue` inside a function called from a loop silently escape into the caller's loop. `_loop_depth` is interpreter-global, not function-scoped. This is the same class of bug as the v2.13.0 top-level break/continue/return fix, but the fix only covered the top-level case.
2. **[C5]** — uncaught `throw` at top level escapes as a `_ThrowSignal` (a `BaseException`) and prints a raw Python traceback. v2.13.0 fixed this for break/continue/return but missed throw.
3. **[I3] / [I4]** — compound assignment operators (`/= 0`, `%= 0`) raise raw Python `ZeroDivisionError`. The plain `1 / 0` path wraps it; the compound path doesn't.
4. **[I12] / [I13]** — `catch (e)` binds `e` in the enclosing scope, silently overwriting any existing binding (including the math constant `e`).
5. **[I15] / [I16]** — nested `funct f` and `class A` use `set` (chain-walk), silently overwriting an outer same-named function/class. Same-syntax-different-meaning footgun.
6. **[I14]** — assignment inside a function silently mutates a same-named global if one exists, but creates a local otherwise. The v2.10.0 closure-mutation feature is the same code path; the lack of `let`/`local` keyword means there's no way to opt out.
7. **[E13]** — `assert(false, "msg")` emitted as `assert(False, 'msg')`, which Python parses as `assert (False, 'msg')` — asserting a 2-tuple, always truthy. **Test never fails.** Silently wrong.
8. **[E21]** — the v2.10.0 closure-mutation feature is wholly broken in emitted Python. The emitter never emits `nonlocal`, so every closure that rebinds an enclosing variable crashes with `UnboundLocalError`.
9. **[I20] / [B41]** — `RotClass`/`RotFunction`/`BoundMethod`/`RotInstance` all print as Python `repr()` when `cout`-ed. `pop([1] | 5)` reports "cannot pop from empty list" even though the list isn't empty.
10. **[I47]** — string/list/dict method access (Python passthrough) exposes ALL Python attributes including `__class__`, `__init__`, `__bases__`. Any rot program can pivot to Python internals.
11. **[L1]** — re-using a `Lexer` instance silently returns the previous tokenize call's output. `Lexer()` is not stateless across `tokenize()` calls.
12. **[L23]** — comment style mismatch: `keywords.py` describes `#`, but the lexer and all examples use `//`. Either docs or lexer is wrong.

---

## Top cross-cutting themes

### Theme 1: chain-walking `Environment.set` is overused

`Environment.set` walks the parent chain — this is the v2.10.0 closure-mutation feature. Method params, `this`, and for-loop vars correctly use `set_local`. But several other declaration-like sites still use `set`, causing silent action-at-a-distance:

- Nested `funct f` clobbers outer `f` (I15)
- Nested `class A` clobbers outer `A` (I16)
- Catch variable `e` clobbers outer `e` / global `e` (I12, I13)
- Builtins are mutable: `cout = "x"` silently shadows the builtin (I17, B59)
- Assignment inside a function silently mutates a same-named global (I14, I71)

**Pattern:** any declaration (function def, class def, catch binding, builtin binding) should use `set_local`. Only user `Assign` should use the chain-walking `set`.

### Theme 2: Python errors leak through to users

A pervasive issue across builtins and several interpreter sites: Python `TypeError`/`ValueError`/`ZeroDivisionError`/`UnicodeDecodeError`/`RecursionError` propagate raw, exposing Python internals to ROT users and breaking the `try`/`catch` contract.

Sites: B4-B9 (`len`, `abs`, `sqrt`, `pow`, `floor`, `ceil`), B13-B16 (`num`), B21-B22 (`min`/`max`), B27-B29 (`range`), B33-B35 (`read_file`/`write_file` encoding), I3-I7 (compound assign + `len`), I10 (recursion), I49-I51 (`input`, file I/O, `rand_int`/`pop`/`round`).

**Pattern:** wrap every Python-level operation in `try/except` and re-raise as `InterpreterError` with a rot-styled message. The cleanest single fix is wrapping `_evaluate_call` (interpreter.py:477-484) for ANY callable.

### Theme 3: error messages have no source location

All `InterpreterError` instances carry `line=0, col=0`, so the CLI prefix `line N:C:` is suppressed (errors.py:10-15). Several `ParserError` raise sites also lack line/col. Users see bare messages like `name 'undefined' is not defined` with no indication where.

Root cause: AST nodes don't carry source positions; the parser has them but doesn't propagate.

### Theme 4: Python-style output for non-scalar / ROT values

`cout`, `coutln`, `str`, f-string interpolation, and the REPL echo all use `_stringify`, which special-cases `None`/`bool`/`int`/`float`/`str` at the top level but falls through to Python `str()` for everything else.

Affected: lists (`[1, 2]` instead of `[1 | 2]`), dicts (Python repr), `RotInstance` (`<rot.interpreter.RotInstance object at 0x...>`), `RotFunction`/`RotClass`/`BoundMethod` (same Python repr), `bytes` (`b'a'` from `.encode()`).

See B1-B3, I21, I39, T48, T112.

### Theme 5: emitter drift across the board

Per the HANDOFF, the emitter is "off the active compile path" but still shipped. The audit confirmed major drift: 12 crash-class issues, 7 wrong-output issues, plus the [E13] silently-always-truthy `assert`.

Headline emitter gaps the HANDOFF didn't mention:
- [E21] `nonlocal` not emitted for closure-mutation (v2.10.0 feature broken in emitted Python)
- [E13] `assert(cond, msg)` silently always passes
- [E12]/[E15]/[E31] no prelude bound — `is_num`, `append`, `pop`, `pi`, `e` all NameError
- [E17] `cout` separator drift (interpreter `sep=""`, emitter Python default `" "`)
- [E1]/[E2]/[E10]/[E11] all builtin stringification (`null`, `true`, `false`, `type`, `str`) Python-leaks
- [E6] `import` is wholly unhandled (raises `NotImplementedError`)

### Theme 6: REPL multi-line input is fragile

`_needs_more` does brace counting but:
- [C11] unterminated string never requests continuation (closing `"` lost forever)
- [C12] same for f-strings
- [C13] `{` inside `// comment` confuses the counter — REPL hangs in `...` forever
- [C14] `KeyboardInterrupt` swallowed by `except BaseException` → no way to interrupt runaway code

### Theme 7: test coverage is partial

`cli.py` and `compiler.py` have NO dedicated tests. `repl.py` has 4 tests. The emitter is tested at ~30% of statement types. Many defensive-error branches are unreachable through any current test. v2.13.0's `BoundMethod` fix is only tested for `init`, not for regular methods. The break/continue scoping bug ([I1]/[I2]) has no test.

---

## Recommended fix order

If you tackle these in order, the maximum number of related findings get fixed per change:

1. **Wrap `_evaluate_call`** (interpreter.py:477-484) with `try/except (TypeError, ValueError, ZeroDivisionError, UnicodeDecodeError, RecursionError, OSError)` → `InterpreterError`. Single change covers I7, I9, I10, B4-B9, B14-B16, B21-B22, B26, B29, I49-I51, I59, B33-B35.
2. **Save/restore `_loop_depth` and `_function_depth`** at function-call entry/exit in `RotFunction.call` and `BoundMethod.call`. Covers I1, I2 plus implicit test gaps T19, T116.
3. **Wrap `Interpreter.execute()` outer boundary** with `try/except _ThrowSignal`. Covers C5, I44, T35.
4. **Switch declaration sites to `set_local`** in interpreter.py:253 (funct), :257 (class), :331 (catch var), and builtin-binding loop at :226-230. Covers I12-I17, I22.
5. **Add an immutable builtins layer** (frozen env). Covers I17, B59.
6. **Add line/col to AST nodes** + thread through every `InterpreterError`. Covers I52, T34, plus 40+ "no location" findings.
7. **Filter dunder access** in MemberAccess Python-getattr fallback. Covers I20, I47, I48.
8. **Refactor `_stringify`** to handle list/dict/RotInstance/RotFunction/RotClass/BoundMethod with ROT-style output (recursive, cycle-detecting, with `|` separators). Covers B1-B3, I21, I39.
9. **REPL `_needs_more`**: track in-string state and skip `//` comments. Covers C11-C13.
10. **REPL `except BaseException`** → narrower handler that re-raises `KeyboardInterrupt`. Covers C14.

---

## Lexer findings

### L1 — `tokenize()` does not reset lexer state
- **Severity:** bug
- **File:line:** `rot/lexer.py:78-86` (`tokenize`) and `rot/lexer.py:70-76` (`__init__`)
- **Repro:** `lex = Lexer(); lex.tokenize("abc"); lex.tokenize("xyz")` returns the tokens from `"abc"`.
- **Observed:** Second call sets `self.source = "xyz"` but `self.pos`, `self.line`, `self.col`, `self.tokens` retain previous state. `while not self._at_end()` immediately exits; returns the prior list.
- **Fix:** Reset state at the top of `tokenize`: `self.source = source; self.pos = 0; self.line = 1; self.col = 1; self.tokens = []`.

### L2 — Bare CR (lone `\r`) does not advance `line`
- **Severity:** bug
- **File:line:** `rot/lexer.py:97-102, 198-206`
- **Repro:** `"\ra\rb\rc"` — three bare CRs.
- **Observed:** Tokens stay on `line=1`; columns increase monotonically. Old-Mac line-ending files get useless error positions.
- **Fix:** in the `\r` branch, after consuming optional trailing `\n`, do `self.line += 1; self.col = 1`.

### L3 — Trailing `\r` captured in COMMENT lexeme on CRLF
- **Severity:** bug
- **File:line:** `rot/lexer.py:127-131` (`_scan_comment`)
- **Repro:** `"// foo\r\nbar"`
- **Observed:** COMMENT lexeme is `"// foo\r"` — trailing `\r` is swallowed.
- **Fix:** stop the comment scan on `\n` OR `\r`.

### L4 — Comment with bare CR (no LF) consumes the rest of the file
- **Severity:** bug
- **File:line:** `rot/lexer.py:127-131`
- **Repro:** `"// foo\r bar"` (CR-only line endings)
- **Observed:** Single COMMENT token `"// foo\r bar"`; nothing after is tokenized.
- **Fix:** same as L3.

### L5 — F-string with unclosed `{` is silently accepted
- **Severity:** bug / fragility
- **File:line:** `rot/lexer.py:159-173` (`_scan_fstring`)
- **Repro:** `f"hi {x"`
- **Observed:** Lexer emits a FSTRING token; the unclosed `{` becomes the parser's problem (with a worse message).
- **Fix:** track brace depth in `_scan_fstring`; on EOF/close-`"` with depth > 0, raise `LexerError("unclosed '{' in f-string")`.

### L6 — Empty `{}` inside f-string accepted by the lexer
- **Severity:** suspect / test gap
- **File:line:** `rot/lexer.py:159-173`
- **Repro:** `f"x{}y"`
- **Fix:** add a parser test for `f"{}"`; if absent, raise a clear error.

### L7 — `{{` / `}}` and `\{` / `\}` not recognized as escapes in f-strings
- **Severity:** bug / fragility
- **File:line:** `rot/lexer.py:159-173`
- **Repro:** `f"{{x}}"`, `f"\{x\}"`
- **Observed:** Both forms lex as a single FSTRING with literal characters; the parser misinterprets braces.
- **Fix:** add `{{`/`}}` handling (Python convention) or `\{`/`\}` (consistent with `\"`).

### L8 — Trailing `\` in string consumes the closing quote
- **Severity:** bug / quality of message
- **File:line:** `rot/lexer.py:175-189`
- **Repro:** `"abc\"` (user means: string with literal backslash)
- **Observed:** `LexerError: unterminated string literal`. The backslash escapes the `"`.
- **Fix:** when raising "unterminated string", check if last consumed char was `\` and add "did you mean `\\`?".

### L9 — Unknown escape sequences silently lose the backslash
- **Severity:** edge case / fragility
- **File:line:** `rot/lexer.py:175-189` + `rot/syntax.py:92-106` (`_decode_string_escapes`)
- **Repro:** `"\q"`
- **Observed:** Lexer keeps `\q`; parser's `_ESCAPE_SEQUENCES.get(esc, esc)` returns `q` and drops the backslash. Silent typo loss.
- **Fix:** raise on unknown escape OR preserve verbatim (`\q`).

### L10 — No `\x..` / `\u....` / `\0` / octal escapes
- **Severity:** edge case / test gap
- **File:line:** `rot/lexer.py:175-189`, `rot/syntax.py` escape table
- **Repro:** `"\x41"` decodes to `x41`, not `A`.
- **Fix:** add hex/unicode/null handling, or raise on `\x`/`\u`/`\0`.

### L11 — Literal newlines inside `"..."` strings silently accepted
- **Severity:** edge case / suspect
- **File:line:** `rot/lexer.py:175-189`
- **Repro:** source containing `"a\nb"` with actual newline.
- **Observed:** STRING_LIT spans multiple lines silently. Unterminated strings can merge content from far below.
- **Fix:** decide policy; reject literal newlines in `"..."` if multi-line strings are not a feature.

### L12 — Triple-quoted strings `"""..."""` lex as three empty strings
- **Severity:** edge case
- **File:line:** `rot/lexer.py:175-189`
- **Repro:** `"""abc"""`
- **Observed:** Three tokens: `STRING_LIT '""'`, `STRING_LIT '"abc"'`, `STRING_LIT '""'`.
- **Fix:** detect and either support or emit "triple-quoted strings are not supported".

### L13 — Scientific notation not supported
- **Severity:** edge case / test gap
- **File:line:** `rot/lexer.py:139-149`
- **Repro:** `1e10` → `NUMBER '1'` + `IDENT 'e10'`.
- **Fix:** consume optional `[eE][+-]?[0-9]+` as part of NUMBER, or document.

### L14 — Hex / binary / octal literals not supported
- **Severity:** edge case / test gap
- **File:line:** `rot/lexer.py:139-149`
- **Repro:** `0x1F` → `NUMBER '0'` + `IDENT 'x1F'`.
- **Fix:** support `0x`/`0b`/`0o` prefixes or emit a friendlier error.

### L15 — Numeric underscore separators not supported
- **Severity:** edge case
- **Repro:** `1_000_000` → `NUMBER '1'` + `IDENT '_000_000'`.
- **Fix:** allow `_` between digits.

### L16 — `5abc` silently produces two tokens
- **Severity:** edge case / fragility
- **File:line:** `rot/lexer.py:139-149`
- **Observed:** No diagnostic for digit-followed-by-letter.
- **Fix:** at end of `_scan_number`, if next char is identifier-start, raise.

### L17 — Lone `.` and `.5` not handled specially
- **Severity:** edge case
- **File:line:** `rot/lexer.py:29`
- **Repro:** `.5` → `DOT` + `NUMBER '5'`.
- **Fix:** lex `.<digit>` as float, or improve error.

### L18 — `&`, `^`, `~` produce bare "unexpected character"
- **Severity:** fragility / quality of message
- **Fix:** small typo table: `&` → "use `and`", `~` → "not supported".

### L19 — `|` is both arg separator and (potential) bitwise — no escape hatch
- **Severity:** language design / fragility
- **File:line:** `rot/lexer.py:28`
- **Fix:** document explicitly.

### L20 — `;` produces bare "unexpected character"
- **Fix:** friendly message: "ROT does not use `;` to terminate statements".

### L21 — `===`/`!==` silently decompose
- **Severity:** fragility
- **File:line:** `rot/lexer.py:113-117`
- **Fix:** after `==`/`!=`, peek for extra `=` and raise friendly.

### L22 — `**`, `++`, `--`, `//` (as int-div) silently decompose
- **Severity:** edge case / fragility
- **Notable:** `a // b` → `IDENT COMMENT '//b'` — `b` is swallowed into a comment.
- **Fix:** add explicit two-char detections with friendly errors.

### L23 — Comment style mismatch: docs say `#`, lexer uses `//`
- **Severity:** documentation drift
- **Note:** Examples all use `//`. Pick one.

### L24 — `=>` silently `SETVALUE GREATERTHAN`
- **Fix:** reserve for future use or error.

### L25 — Single quote `'` errors bare
- **Fix:** "ROT only supports double-quoted strings".

### L26 — Vertical tab / NBSP / em space / zero-width error
- **Severity:** edge case
- **Fix:** widen whitespace OR detect invisibles with hint.

### L27 — Unicode identifiers silently accepted (any `isalpha()`)
- **Severity:** suspect / test gap
- **Fix:** decide ASCII-only vs Unicode; document.

### L28 — UTF-8 BOM at start raises bare error
- **Fix:** strip leading `﻿` in `tokenize`.

### L29 — Null bytes outside strings error bare
- **Fix:** optional — improve message.

### L30 — Non-string input crashes with Python error
- **Severity:** API hygiene
- **Fix:** type-check at top of `tokenize`.

### L31 — `_peek(-1)` would wrap to last char
- **Severity:** fragility
- **Fix:** bounds-check `0 <= i < len`.

### L32 — No EOF sentinel token
- **Severity:** fragility
- **Fix:** append `Token("", "EOF", ...)` at end of `tokenize`.

### L33 — Token has no end-position / span
- **Severity:** fragility (limits error UX)
- **Fix:** add `end_line`, `end_col`.

### L34 — `_log` width formatting is fragile
- **Fix:** use `f"{idx:>5} | {token.lexeme!r:<10} | {token.kind}"`.

### L35 — Keyword reservation is enforced by parser, not lexer
- **Severity:** suspect

### L36 — `iffy`, `returns`, `truex` correctly lex as IDENT (not bug; verify)
- **Severity:** test gap — add explicit tests.

### L37 — KEYWORDS table missing parametric test
- **Fix:** `@pytest.mark.parametrize("word,kind", KEYWORDS.items())`.

### L38 — No f-string tests in test_lexer.py
- **Severity:** test gap

### L39 — No tests for CRLF / tabs / multi-line-string position tracking
- **Severity:** test gap (would catch L2)

### L40 — No tests for number edge cases (`1.`, `.5`, `1e10`)
- **Severity:** test gap

### L41 — No test verifying lexer state isolation across calls
- **Severity:** test gap (would catch L1)

### L42 — No test for `trace=True` mode
- **Fix:** add `capsys`-based test.

### L43 — No CRLF test for COMMENT lexeme cleanliness
- **Severity:** test gap (would catch L3)

### L44 — No tests for empty / whitespace-only / comment-only sources
- **Severity:** test gap

### L45 — `_SOLO_FALLBACK` paths (`<`, `>` standalone) untested
- **Severity:** test gap

### L46 — `_TWO_CHAR_TOKENS` lookup with EOF only works by accident
- **Severity:** fragility — add explanatory comment.

### L47 — `_SINGLE_CHAR_TOKENS` vs `_SOLO_FALLBACK` ordering
- **Fix:** merge into one table or add a comment.

### L48 — Mixed-whitespace runs (`\t \t`) collapse into one SPACE
- **Severity:** suspect — document.

### L49 — "Unterminated string" error col points at opening, not EOF
- **Fix:** include current line in the message.

### L50 — `_scan_fstring` and `_scan_string_literal` are near-duplicates
- **Severity:** fragility — extract a helper.

### L51 — f-string lexeme position inconsistency
- **Severity:** suspect — pick a convention.

### L52 — Escape decoding split between lexer and parser
- **Severity:** fragility — document the split.

### L53 — No length limit on identifier / string / number
- **Severity:** suspect / DoS-adjacent

### L54 — `_at_end` re-checks rely on `_peek` returning `""`
- **Severity:** edge case (currently safe but fragile)

### L55 — `trace=True` always prints to stdout (no stream injection)
- **Fix:** accept `trace_stream`.

### L56 — Per-token `if self.trace` branch (negligible)

### L57 — `keywords.py` docstring claims "lowercase letters" but lexer accepts mixed case
- **Severity:** documentation drift

### L58 — Case-sensitive keywords: `If`, `IF`, `iF` silently become IDENT
- **Fix:** detect via `lexeme.lower() in KEYWORDS` and offer "did you mean?".

### L59 — `Token` has no `__post_init__` type validation
- **Severity:** fragility

### L60 — `Lexer.tokens` is publicly mutable
- **Fix:** return a copy.

### L61 — Unterminated-string error has no suggestion
- **Fix:** add "did you forget a closing `\"`?".

### L62 — f-string with literal newlines silently accepted
- **Severity:** edge case

### L63 — `isalpha()` accepts `ñ` but rejects emoji — inconsistent
- **Fix:** pick a Unicode policy.

### L64 — Lexer doesn't expose original source for downstream error messages
- **Fix:** thread source through.

### L65 — Invisibles in error messages just show `\xa0` repr
- **Fix:** see L26.

### L66 — `import f"path"` would lex as IMPORT FSTRING (parser rejects)
- **Severity:** suspect

---

## Parser findings

### Operator precedence and grammar bugs

### P1 — `not` is allowed as RHS of any binary op
- **Severity:** bug — parser accepts `x = a + not b` and similar; produces nonsensical AST that the interpreter may stumble on.
- **File:line:** `rot/syntax.py:_parse_prefix` / Pratt loop
- **Fix:** require `not` to occur only at prefix position with proper precedence.

### P2 — Chained comparison silently produces wrong AST
- **Severity:** bug
- **Repro:** `a == b == c`
- **Observed:** Parses as `(a == b) == c` (Python idiom for "both-equal" not honored). May produce surprising boolean comparisons.
- **Fix:** either match Python semantics (chain) or reject.

### P3 — `not a == b` precedence
- **Severity:** suspect — verify whether `not (a == b)` or `(not a) == b`.

### P4 — `-2 ** 3` precedence (if `**` ever exists)
- **Severity:** suspect — N/A today.

### P5 / P68 — Bare `{}` always parses as a dict, never as a block
- **Severity:** missing feature — no way to write a scope block.

### P6 — `else if` (two-word) not accepted; only `elseif`
- **Severity:** missing feature

### P7 — Trailing `|` in `[a | b |]` rejected with cryptic error
- **Severity:** edge case

### P8-P12 — Missing: `finally`, multi-catch, typed catch, bare `throw`, paren-vs-pipe inconsistency
- **Severity:** missing feature

### P13 — `return return 5` parses as two statements
- **Severity:** bug

### P14, P16, P44, P75, P97, P99, P116, P125, P133 — Validations deferred to runtime that could be parser-level
- **Severity:** suspect

### P15 — No statement separator support (no `;`, no newline-as-separator enforcement)
- **Severity:** fragility

### P18-P22 — Missing: hex / octal / binary literals, scientific notation, `**`, bitwise, `**=`/`//=`
- **Severity:** missing feature

### P23 — Error messages mention internal token kinds (`COMMA`, `L_PAREN`)
- **Severity:** error quality

### P24-P28 — Missing f-string features: format specs, nested f-strings, `{{`/`}}` escapes, line/col propagation, inner-quote escapes
- **Severity:** missing feature

### P29-P30 — Silent escape-decoder data loss (covered also at L9-L10)

### P31-P33 — Single quotes, triple quotes, raw `\n` in strings — not supported, no friendly error
- **Severity:** missing feature

### P34-P36 — No default params, no varargs, no kwargs
- **Severity:** missing feature

### P37-P42 — No static methods, class-body limitations, no `extends`, no `super`
- **Severity:** missing feature

### P40 — Duplicate `init` methods in a class — silent accept
- **Severity:** bug — second `init` silently wins, no warning.

### P43 — `this = 5` parses as a normal Assign (should reject)
- **Severity:** bug

### P48-P51 — Missing: multi-var for-loop, paren consistency between for/if/while, ternary
- **Severity:** missing feature

### P53-P54 — Missing: `from ... import`, `import ... as`; empty `import ""` accepted
- **Severity:** missing feature

### P55, P80-P82 — AST schema asymmetry (Assign vs IndexAssign vs MemberAssign; Program vs Block)
- **Severity:** suspect

### P56-P57, P70, P88, P94-P95 — Precedence/op coupling to lexemes, magic number `4` in `_parse_prefix`, docstring drift
- **Severity:** fragility

### P59, P60, P66, P73, P100, P110, P112 — Error messages miss line/col, are misleading
- **Severity:** error quality

### P76-P78 — No AST source locations, no `Compare` node, no `Lambda`
- **Severity:** missing feature

### P88 / P104 — Documented precedence in docstring doesn't match the code
- **Severity:** fragility

### P89 — Missing tests for IndexAssign, MemberAssign, MemberAccess, Index, ClassDef, TryCatch, ThrowStmt, ImportStmt, ForStmt, BreakStmt, ContinueStmt, ListLit, DictLit, f-strings, method calls, compound member/index assign, error-line/col assertions
- **Severity:** massive test gap

### P91 — `FSTRING` missing from `_EXPR_STARTS` → `return f"..."` silently splits
- **Severity:** bug

### P100 — Off-by-one missing: `_advance` accesses `self.tokens[self.pos]` without bound check
- **Severity:** fragility

### P103 — No `;` statement terminator support — lexer rejects
- **Severity:** missing feature

### P106 — No slice notation
- **Severity:** missing feature

### P125 — Validations deferred to runtime
- **Severity:** suspect

### P127-P136 — Specific test gaps:
- IndexAssign tests
- MemberAssign tests
- MemberAccess tests
- Index tests
- ClassDef tests
- TryCatch tests
- ThrowStmt tests
- ImportStmt tests
- ForStmt tests
- BreakStmt/ContinueStmt tests

### P138-P141 — `THIS` half-special-cased; `_NAME_LIKE` inconsistency
- **Severity:** fragility

### P151 — Test file covers only ~30% of grammar productions
- **Severity:** massive test gap

### P153-P160 — Smaller items:
- `\\` correctly decodes (works)
- `_parse_atom_or_call` loops indefinitely on `()`/`[]`/`.` chains (works for legit chains; no depth limit)
- AST `Block` not first-class statement type (can't have `{ ... }` as standalone)
- `_parse_atom` raises but doesn't note `=` / `|` ambiguity
- `_advance` no bound check
- `test_unterminated_block_raises_parser_error` doesn't assert the message
- `_TWO_CHAR_TOKENS` doesn't include `||`, `&&`, `<<`, `>>`, `->`, `=>`, `**`

(See parser agent's full report for P17, P32, P38, P41, P42, P45-P47, P52, P56, P58, P61-P67, P69, P71-P74, P79, P83-P87, P90, P92-P93, P96, P98, P101-P102, P105, P107-P109, P111, P113-P115, P117-P124, P126, P137, P142-P150, P152, etc. — all numbered P1-P160 in the auditor's report. The above represents the highest-severity subset.)

---

## Interpreter findings

### Critical: control-flow signals escape function boundaries

### I1 — `break` inside a function called from a loop escapes to the caller's loop
- **Severity:** bug
- **File:line:** `rot/interpreter.py:125-145` (RotFunction.call), `:196-218` (BoundMethod.call)
- **Repro:**
  ```
  funct quit() { break }
  for i in range(5) {
      coutln(i)
      quit()
      coutln("after quit")
  }
  ```
- **Observed:** prints `0` only. `_BreakSignal` propagates through `RotFunction.call`. `_loop_depth` is interpreter-global.
- **Fix:** save/restore `_loop_depth = 0` at function entry/exit. Catch `_BreakSignal`/`_ContinueSignal` in `call` and re-raise as `InterpreterError`.

### I2 — `continue` inside a function called from a loop escapes to the caller's loop
- **Severity:** bug
- Same root cause as I1.

### I3 — `x /= 0` and `x %= 0` (Assign compound) raise raw `ZeroDivisionError`
- **Severity:** bug
- **File:line:** `rot/interpreter.py:271`
- **Fix:** wrap the compound-op call in try/except.

### I4 — `xs[i] /= 0`, `c.x /= 0` (IndexAssign/MemberAssign compound) raise raw `ZeroDivisionError`
- **Severity:** bug
- **File:line:** `rot/interpreter.py:351, 367, 380`
- **Fix:** add `ZeroDivisionError` to existing wrappers.

### I5 — `s -= 1` (string compound) raises raw `TypeError`
- Same fix as I3.

### I6 — `null += 1` raises raw `TypeError`
- Same fix as I3.

### I7 — `len(null)`, `len(5)`, `len(funct)` raise raw `TypeError`
- **File:line:** `rot/builtins.py:211`
- **Fix:** wrap `_evaluate_call` in interpreter.py to convert Python exceptions.

### I8 — `num("abc")`, `num(null)`, `num([])` raise raw `ValueError`
- **File:line:** `rot/builtins.py:29-39`

### I9 — `min([])`, `max([])`, `min()`, `max()` raise raw `ValueError`
- **File:line:** `rot/builtins.py:101-110`

### I10 — Unbounded recursion raises raw `RecursionError`
- **File:line:** `rot/interpreter.py:125-145`
- **Fix:** catch and re-raise as `InterpreterError("call stack too deep")`.

### Environment / scope bugs

### I11 — Variables declared in if / while / for / try blocks leak to enclosing scope
- **Severity:** suspect / fragility
- **File:line:** `rot/interpreter.py:397-399` (`_execute_block` pushes no new env)
- **Repro:** `if (true) { z = 5 }\ncoutln(z)` → `5`.

### I12 — Catch variable leaks to enclosing scope and silently clobbers existing bindings (including math `e`)
- **Severity:** bug
- **File:line:** `rot/interpreter.py:331, 337`
- **Repro:** `coutln(e)` prints `2.718…`; `try { throw "x" } catch (e) {}`; `coutln(e)` prints `x`.
- **Fix:** push new env around catch block; use `set_local` for catch var.

### I13 — Catch variable creates new global when no prior `e`
- Same root cause as I12.

### I14 — Assignment in a function creates local OR mutates global depending on context
- **Severity:** bug / footgun
- **File:line:** `rot/interpreter.py:101-109` (`Environment.set`)
- **Fix:** add explicit `let`/`local` keyword OR change `set` to always-local.

### I15 — Nested `funct f` clobbers outer `f`
- **Severity:** bug
- **File:line:** `rot/interpreter.py:253` (uses chain-walking `set`)
- **Fix:** use `set_local`.

### I16 — Nested `class A` clobbers outer `A`
- Same fix as I15: line 257 use `set_local`.

### I17 — Builtins are mutable and silently overwritable
- **Severity:** bug / footgun
- **File:line:** `rot/interpreter.py:226-230`
- **Repro:** `pi = 3.0`, `cout = "x"` both silently succeed.

### Class / method / `this` bugs

### I18 — `init` returning a value is silently ignored
- **Severity:** bug / error quality
- **File:line:** `rot/interpreter.py:156-165`
- **Fix:** raise on non-bare return inside init.

### I19 — `MyClass.method()` fails with cryptic `no member 'method' on RotClass`
- **Severity:** error quality / missing feature

### I20 — `RotClass` internals leak via member access (`A.methods`, `A.name`, `A.closure`, `A.call`)
- **Severity:** bug (info leak)
- **File:line:** `rot/interpreter.py:431-438`
- **Fix:** give `RotClass` and `BoundMethod` their own `get_member` with no Python fallback.

### I21 — `cout(instance)` / `str(funct)` print Python repr
- **Severity:** bug (output quality)
- **File:line:** `rot/builtins.py:18-26` (`_stringify`)

### I22 — Reassigning `this` inside a method silently mutates the binding
- **Severity:** suspect / fragility

### I23 — `super` produces bare `name 'super' is not defined`
- **Severity:** error quality / missing feature

### I24 — `class B extends A {}` produces cryptic parser error
- **Severity:** error quality

### I25 — `type(A)` returns `"function"` for a class
- **Severity:** error quality
- **File:line:** `rot/builtins.py:141-142`
- **Fix:** return `"class"`.

### Operators / arithmetic

### I26 — `null < 5` errors but `null == 5` works (false) — inconsistent
- **Severity:** suspect

### I27 — Wrapped error messages include Python phrasing (`unsupported operand types ...`, `NoneType`)
- **Severity:** error quality
- **File:line:** `rot/interpreter.py:457-461`

### I28 — `5 / 2` returns `2.5`; `5 % 2` returns int — inconsistent for integer operands
- **Severity:** suspect / documentation
- **Fix:** add `//` for integer division.

### I29 — Float overflow silently produces `inf`
- **Severity:** suspect

### I30 — `true + 1`, `[1][true]` work via Python bool-as-int, inconsistent with `is_num(true) == false`
- **Severity:** suspect

### I31 — `list + number` produces wrapped TypeError with Python phrasing
- **Severity:** error quality

### I32 — `list[1.0]` errors but `list[true]` succeeds (Python's `True == 1`)
- **Severity:** suspect

### Indexing / strings / slicing

### I33 — Slicing (`s[1:3]`, `xs[0:2]`) not supported
- **Severity:** missing feature
- **File:line:** `rot/syntax.py` Index parser

### I34 — String mutation via index produces wrapped TypeError with Python phrasing
- **Severity:** error quality
- **Fix:** detect string target and emit "strings are immutable".

### I35 — Missing dict key produces `index error: 'k'` — no indication it's a dict
- **Severity:** error quality

### I36 — `dict.method()` works but `dict.key` fails — inconsistent
- **Severity:** suspect

### I37 — `type(dict.keys())` returns `"dict_keys"` (Python type name leak)
- **Severity:** bug (info leak)
- **File:line:** `rot/builtins.py:141-143`

### F-strings

### I38 — F-string format specs (`{x:>5}`, `{3.14:.2f}`) not supported
- **Severity:** missing feature

### I39 — F-string of RotInstance/RotFunction/RotClass/BoundMethod leaks Python repr
- **Severity:** bug (output quality)

### Imports / modules

### I40 — Circular imports succeed silently but leave module partially loaded
- **Severity:** bug
- **File:line:** `rot/interpreter.py:506-532`
- **Fix:** track `_importing` stack; raise `InterpreterError("circular import: ...")`.

### I41 — Import-time errors don't include the imported module's path
- **Severity:** error quality

### I42 — No way to re-import within a session
- **Severity:** missing feature

### try/catch/throw

### I43 — No `finally` clause; try requires catch
- **Severity:** missing feature

### I44 — Uncaught `throw` escapes as `_ThrowSignal` (BaseException) → Python traceback
- **Severity:** error quality (and bug — covered also by C5)
- **Fix:** wrap `Interpreter.execute` outer boundary.

### I45 — `try/catch` shape inconsistent: throw value typed, caught Python exception stringified
- **Severity:** suspect / error quality
- **File:line:** `rot/interpreter.py:331, 337`

### I46 — try/catch catches RecursionError, MemoryError, SystemError, etc.
- **Severity:** suspect
- **Fix:** narrow to `InterpreterError`.

### Built-ins (selected — see also Builtins section)

### I47 — String/list/dict Python-getattr fallback exposes `__class__`, `__init__`, `__bases__`
- **Severity:** bug (info leak / security)
- **File:line:** `rot/interpreter.py:433-438`
- **Fix:** reject names starting with `_`, or whitelist per type.

### I48 — `"a".encode()` returns Python `bytes` → `b'a'` leaks
- **Severity:** bug
- Same root cause as I47.

### I49 — `_builtin_input` catches `EOFError` but not `KeyboardInterrupt`
- **Severity:** edge case

### I50 — `_read_file`/`_write_file` don't catch `UnicodeDecodeError`/`UnicodeEncodeError`
- **Severity:** edge case
- **File:line:** `rot/builtins.py:51-64`

### I51 — `_rand_int`, `_builtin_range`, `_builtin_pop`, `_builtin_round` raw-`int()` non-numeric input
- **Severity:** edge case

### Error quality / source location

### I52 — All runtime errors have no source location (line=0, col=0)
- **Severity:** error quality (pervasive)
- **Fix:** add line/col to AST nodes.

### I53 — `not callable: <callee>` uses Python repr
- **File:line:** `rot/interpreter.py:484`

### I54 — `print(...)`, `None`, `True`, `False`, `def`, `import xxx` produce bare `name X is not defined`
- **Severity:** error quality
- **Fix:** in `Environment.get`, suggest rot equivalents.

### Closures / nesting

### I55 — Closures capture loop var by reference (late binding); all closures see final value
- **Severity:** suspect (Python footgun inherited)
- **Repro:**
  ```
  fns = []
  for i in [1|2|3] { funct f() { return i } append(fns | f) }
  for g in fns { coutln(g()) }   # → 3, 3, 3
  ```

### Test gaps (I56-I75)
- I56 break/continue inside function from loop (would catch I1, I2)
- I57 compound `/= 0` (I3, I4)
- I58 catch variable scoping (I12, I13)
- I59 nested funct/class clobbering (I15, I16)
- I60 `len(null)`/`num("abc")`/`min([])` (I7, I8, I9)
- I61 circular imports (I40)
- I62 unbounded recursion (I10)
- I63 reassigning builtins (I17)
- I64 dunder leak (I47)
- I65 Python type leak (I37)
- I66 class.method access (I19)
- I67 f-string format specs (I38)
- I68 init returning value (I18)
- I69 `try { break } catch (e) {}` doesn't swallow break
- I70 closures capturing loop var (I55)
- I71 RotInstance truthiness (always true)
- I72 RotInstance == RotInstance (identity equality)
- I73 List passed by reference (mutation visible)
- I74 imports lazy inside function/if
- I75 `cout(instance)` Python repr (I21)

### Misc fragility (I76-I82)
- I76 `_execute_statement` is long isinstance chain
- I77 `RotFunction.call` and `BoundMethod.call` near-duplicate
- I78 `_BINARY_OPS` anonymous lambdas
- I79 No `define` operation for explicit local declaration
- I80 `_stringify` import dependency-ordering fragility
- I81 Interpreter state not reset between `execute()` calls (REPL implications)
- I82 `Environment.get` error message inconsistent quoting

---

## Builtins findings

### B1 — `cout`/`coutln` render lists, dicts, instances in Python style
- **Severity:** bug (consistency)
- **File:line:** `rot/builtins.py:18-26`, `rot/interpreter.py:487-492`
- **Repro:** `coutln([1 | 2 | true | null])` → `[1, 2, True, None]`
- **Fix:** recursive `_stringify` over collections.

### B2 — `_stringify` of RotInstance shows Python default repr
- **Severity:** bug
- **Fix:** `f"<{x.cls.name} instance>"` or `to_string` hook.

### B3 — `_stringify` of RotFunction/RotClass/BoundMethod shows Python repr
- **Severity:** bug

### B4-B9 — `len`/`abs`/`sqrt`/`pow`/`floor`/`ceil` leak Python `TypeError`
- **Severity:** error quality
- **Fix:** wrap each.

### B7 — `abs(true)` returns `1` (Python bool=int silent)
- **Severity:** inconsistency

### B10 — `pow(-1, 0.5)` returns Python complex
- **Severity:** bug
- **Repro:** `coutln(pow(-1 | 0.5))` → `(6.123e-17+1j)`

### B11 — 3-arg `pow(b, e, m)` modular pow undocumented
- **Severity:** inconsistency

### B12 — `num(bool)` returns int; inconsistent with `is_num(bool) == false`
- **Severity:** inconsistency

### B13-B16 — `num()` leaks `ValueError` for null, empty string, "abc", list/dict
- **Severity:** bug / error quality

### B17 — `num()` hex/scientific inconsistency
- **Severity:** inconsistency

### B18 — `num()` of whitespace-padded string silently strips
- **Severity:** suspect

### B19 — `num()` arity errors leak `_num()` Python name
- **Severity:** error quality

### B20 — `str`, `type`, `is_*`, `read_file`, `write_file`, `rand_int`, `rand_float`, `assert` all leak underscore-prefixed Python names in arity errors
- **Severity:** error quality (widespread)

### B21-B22 — `min`/`max` empty / no-args leak Python `ValueError`
- **Severity:** error quality

### B23 — `min(1)` returns 1 (suspect)

### B24 — `min("foo")` returns `"foo"` not `"f"` — string excluded from iterable path
- **Severity:** bug / inconsistency

### B25 — `min(dict)` returns smallest key without explanation
- **Severity:** suspect

### B26 — `min`/`max` mixed types leak Python `TypeError`
- **Severity:** error quality

### B27 — `range(0|3|0.5)` errors with "step must not be zero" — wrong reason (float silently truncated to 0)
- **Severity:** bug

### B28 — `range` silently truncates float args
- **Severity:** suspect

### B29 — `range` of wrong type leaks `ValueError`
- **Severity:** error quality

### B30 — `_builtin_input` checks `prompt != ""` instead of arg-presence
- **Severity:** suspect

### B31 — `input` prompt uses Python `str()` not `_stringify`
- **Severity:** inconsistency

### B32 — `input` arity error leaks Python signature

### B33 — `read_file` of binary leaks `UnicodeDecodeError`
- **Severity:** bug + error quality

### B34 — `read_file` opens without explicit encoding (platform-dependent)
- **Severity:** bug

### B35 — `write_file` opens without explicit encoding

### B36 — `write_file` always overwrites — no append mode
- **Severity:** missing feature

### B37 — `write_file` uses Python `str(content)` not `_stringify`
- **Severity:** inconsistency

### B38 — `write_file` returns None silently — no documented return
- **Severity:** inconsistency / minor

### B39 — `append` arity error leaks Python signature
- **Severity:** error quality

### B40 — `append` mutates+returns None, not documented

### B41 — `pop([1] | 5)` reports "cannot pop from empty list" — WRONG message
- **Severity:** bug

### B42-B46 — `pop`/`rand_int` arity / type validation gaps
- **Severity:** error quality

### B47 — No way to seed RNG; module-level random shared
- **Severity:** missing feature

### B48 — `rand_float(1)` leaks Python error
- **Severity:** error quality

### B49 — No `rand_float(lo, hi)` overload
- **Severity:** missing

### B50 — `assert()` leaks Python error
- **Severity:** error quality

### B51 — `assert` silently accepts extra args

### B52 — `assert` message uses `str()` not `_stringify`
- **Severity:** inconsistency

### B53 — `assert` error has no `assert:` prefix
- **Severity:** error quality

### B54 — `is_func(class)` returns true; `type(class)` returns "function"
- **Severity:** inconsistency
- **Fix:** introduce `"class"` type and `is_class`.

### B55 — `type(len)` returns `"builtin_function_or_method"` (Python leak)
- **Severity:** suspect

### B56 — `is_null(0)` returns false (correct; verify)

### B57 — `is_bool(1)` returns false (correct; no test)

### B58 — `is_num(true)` returns false (correct; no test)

### B59 — Builtins shadowable via user assignment
- **Severity:** suspect / design
- **Repro:** `len = 99; coutln(len)` → `99`.

### B60 — `cout`/`coutln` live in interpreter.py, others in builtins.py — split
- **Severity:** maintainability

### B61 — Recursive list/dict in `cout` shows Python `[...]` ellipsis
- **Severity:** edge case

### B62 — No `print` alias for newcomers

### B63 — Missing common builtins (`sum`, `sorted`, `reversed`, `keys`/`values`/`items`, `chr`/`ord`, `int`/`float`, `exit`, `time`, `seed`, etc.)
- **Severity:** missing

### B64 — `type(true) == "int"` returns false (correct; no test)

### B65 — `is_func(len)` returns true (correct; no test)

### B66 — No tests for `cout()`/`coutln()` with 0 args, multi args, null, instance

### B67 — No tests for many builtin error paths

### B68 — No tests for `is_func`, `is_bool(true/false)`, `type(func)`

### B69 — No test for `input` EOF

### B70 — No test for `write_file` error, `read_file` binary

### B71 — No test for `pi`/`e` shadowability

### B72 — `cout`/`coutln` accept any arg count silently — undocumented

### B73 — `_stringify` import circular-import smell

### B74 — Caught Python `TypeError` exposes raw Python message in catch var
- **Severity:** bug — driven by B4-B9 leaks.

### B75 — Repeated `int(arg)` pattern — extract `_to_int`

### B76 — `round(2.5) == 2` banker's rounding (Python default)
- **Severity:** suspect

### B77 — `round(x, digits)` with non-int digits silently coerces

### B78 — `floor(5)` int but `sqrt(16) = 4.0` float — inconsistent

### B79 — No `abs(complex)` handling, and `pow` produces complex
- **Severity:** edge case

### B80 — `len(d.keys())` works but no native `keys()`/`values()`/`items()` builtin

### B81 — `is_func` lazy import not cached
- **Severity:** suspect / micro-perf

### B82 — `BUILTINS` is module-level mutable dict
- **Severity:** hardening

### B83 — No `__all__` in builtins.py

### B84 — `floor`/`ceil`/`abs` of NaN/Inf untested

### B85 — `min`/`max` `hasattr(x, "__iter__")` is loose
- **Severity:** edge case

### B86 — `_builtin_type` returns user class name verbatim — collision possible
- **Repro:** `class int {}` — `type(int())` returns `"int"`, indistinguishable from real int.

### B87 — No way to introspect builtin names

---

## Emitter findings

The emitter is "off the active path" but kept tested. Drift was found in 12 crash-class issues, 7 wrong-output issues, and one silent-correctness issue.

### E1 — `null` literal prints as `None`
- **File:line:** `rot/emitter.py:119-120`

### E2 — `true`/`false` print as `True`/`False`
- **File:line:** `rot/emitter.py:117-118`

### E3 — `+` does not perform ROT's string coercion
- **Severity:** crash
- **File:line:** `rot/emitter.py:127-130`
- **Repro:** `cout("count = " + 5)` → emitted Python raises `TypeError`.

### E4 — `throw <value>` always raises `Exception(value)` — loses non-string payloads
- **Severity:** drift

### E5 — `try/catch` doesn't differentiate user-throw vs Python exception
- **Severity:** drift

### E6 — `import "path"` wholly unhandled — `NotImplementedError`
- **Severity:** crash / missing
- **File:line:** `rot/emitter.py:88-89`

### E7 — `this` emitted as bare `this`, not `self` — crash inside class methods
- **Severity:** crash
- **File:line:** `rot/emitter.py:111-112`

### E8 — Lists print as Python lists (covered also by E1/E2)

### E9 — F-strings + `+`-coercion failure
- **Severity:** crash

### E10 — `str(...)` emits Python's `str` — mis-stringifies `null`/`true`/`false`
- **Severity:** wrong output
- **File:line:** `rot/emitter.py:143-155`

### E11 — `type(...)` returns Python type names

### E12 — `is_num`/`is_str`/`is_*`/`rand_int`/`pop`/`append`/`pi`/`e`/etc. unbound → NameError
- **Severity:** crash
- **Fix:** emit a prelude.

### E13 — `assert(cond, msg)` becomes `assert(False, 'msg')` → asserting 2-tuple → ALWAYS TRUTHY
- **Severity:** silently wrong (most dangerous emitter bug)
- **File:line:** `rot/emitter.py:143-155`

### E14 — `range(...)` returns range object in Python, list in ROT — drift on `cout(range(3))`

### E15 — `pop`/`append` (free-function form in ROT) unbound in Python

### E16 — `cout()` no args matches (`print(end="")`)

### E17 — Multi-arg `cout(a, b)` emitter uses Python default `sep=" "`; interpreter uses `sep=""` — drift in spacing
- **File:line:** `rot/emitter.py:148-153`

### E18 — F-strings inherit `str()` Python-vs-ROT drift (E10)

### E19 — Member-assign chain emission looks correct

### E20 — `def f(a,b,c)` no space after comma — cosmetic

### E21 — Closure-mutation feature (v2.10.0) wholly broken: no `nonlocal` emitted
- **Severity:** crash
- **File:line:** `rot/emitter.py:29-32`
- **Repro:** `make_counter` example crashes with `UnboundLocalError`.

### E22 — For-loop variable interaction roughly aligns

### E23 — `MemberAccess` `this.x` emits `this.x` (instance of E7)

### E24 — `MemberAssign` `this.x = ...` emits `this.x = ...` (instance of E7)

### E25 — Empty class with methods placement (non-issue)

### E26 — `obj.cout()` non-issue

### E27 — String literal emission via `repr()` (acceptable)

### E28 — Unary `not x` spacing (acceptable)

### E29 — `and`/`or` short-circuit matches (E2 still drifts)

### E30 — `/` and `%` match Python 3 semantics

### E31 — `pi`/`e` constants unbound → NameError
- Same prelude fix as E12.

### E32 — Dict iteration order matches

### E33 — Python passthrough methods (`.upper()`) align

### E34 — `_emit_call` does not parenthesize composite callee
- **Severity:** wrong precedence
- **Repro:** `(a + b)()` emitted as `a + b()`.

### E35 — Empty Program (non-issue)

### E36 — `Block` only via `_emit_block` (non-issue)

### E37 — `ElifBranch` walked correctly

### E38 — `Program` top-level (non-issue)

### E39 — `def`-rendering duplicated between FuncDef and ClassDef methods — cosmetic drift risk

### E40 — `repr()` strings handle escapes acceptably

### AST nodes the emitter does not handle at all
- **`ast.ImportStmt`** — no case, falls through to `NotImplementedError`. (See E6.)

All other AST nodes have at least a case (correct or not).

---

## CLI / REPL / Compiler / Errors findings

### C1 — PermissionError on source file leaks traceback
- **Severity:** bug
- **File:line:** `rot/cli.py:62-64`
- **Fix:** broaden `except` to `OSError` and route through `parser.error`.

### C2 — IsADirectoryError on directory leaks traceback
- Same fix.

### C3 — UnicodeDecodeError on non-UTF-8 file leaks traceback
- **Fix:** `read_text(encoding="utf-8")` + catch.

### C4 — UTF-8 BOM crashes lexer with `﻿`
- **Fix:** `encoding="utf-8-sig"` or strip in lexer (L28).

### C5 — Top-level uncaught `throw` leaks `_ThrowSignal` Python traceback
- **Severity:** bug (high impact — v2.13.0 missed this)
- **File:line:** `rot/interpreter.py:321-323`
- **Fix:** wrap `Interpreter.execute` with `try/except _ThrowSignal`.

### C6 — Deep recursion leaks `RecursionError` traceback
- **Severity:** bug
- **Fix:** catch in `Compiler.parse`/`Compiler.run`.

### C7 — PermissionError on imported file leaks traceback
- **File:line:** `rot/interpreter.py:515-516`

### C8 — `--no-run` with no file silently launches REPL
- **Severity:** edge case
- **Fix:** `parser.error` if flag+no-file.

### C9 — `--trace` with no file silently launches non-traced REPL

### C10 — `--repl` with positional file silently ignores file
- **Severity:** edge case (doc says "equivalent")

### C11 — REPL unterminated `"` never requests continuation
- **Severity:** bug
- **File:line:** `rot/repl.py:75-96`
- **Fix:** `return depth > 0 or in_string`.

### C12 — REPL unterminated `f"` same root cause as C11

### C13 — REPL `{` inside `// comment` confuses brace counter — hangs forever
- **Severity:** bug
- **Fix:** in `_needs_more`, skip `// ... \n` runs.

### C14 — REPL Ctrl-C swallowed by `except BaseException` — no way to interrupt runaway code
- **Severity:** bug
- **File:line:** `rot/repl.py:70-72`
- **Fix:** narrow `except`.

### C15 — REPL `""` echoes as blank line — confusing

### C16 — REPL `null` silently suppressed (vs Python's `None` echo)

### C17 — REPL no `exit`/`quit`/`:q`/`.help` commands

### C18 — `pathlib.read_text()` uses locale encoding, not UTF-8
- **Fix:** add `encoding="utf-8"`.

### C19 — `read_file`/`write_file`/`import` all open without `encoding=`
- Same fix.

### C20 — InterpreterError carries no source location
- **Severity:** error quality (pervasive)
- **Fix:** see I52.

### C21 — Many ParserError raises omit line/col
- **File:line:** `rot/syntax.py:123, 173, 223, 292, 319, 412, 535`

### C22 — Error messages expose internal token-kind names (`COMMA`, `L_PAREN`)
- **Fix:** add `_TOKEN_DISPLAY` mapping.

### C23 — No source-line + caret rendering in errors
- **Severity:** error quality

### C24 — No persistent REPL history
- **Fix:** `readline.read_history_file` + atexit.

### C25 — No tab completion in REPL

### C26 — `cout()` doesn't flush — pipe output may be delayed
- **Fix:** `print(..., flush=True)`.

### C27 — `Compiler.parse()` trace prints to stdout — mixes with program output
- **Fix:** trace to stderr.

### C28 — `--trace` "Process 2 - Parser" prints one-line stat, not AST

### C29 — `colorama.init` called on every Compiler construction

### C30 — No tests for CLI/REPL
- **Severity:** test gap

### C31 — Exit codes not documented

### C32 — `emitter.py` is dead-but-present code (no exposure path)
- **Severity:** suspect / dead code

### C33 — `output.py` at repo root is a v1 leftover

### C34 — `rot/__init__.py` exposes only `__version__` — no public API

### C35 — `--trace --no-run` suppresses success marker

### C36 — Stale grammar comment in `syntax.py` (says v2.2.0)

### C37 — Stale comment in `keywords.py` (references `PY_EQUIVALENT`, `rot/parser.py`)

### C38 — Bare CR doesn't bump line counter (duplicate of L2)

### C39 — REPL calls private `interp._evaluate`
- **Severity:** encapsulation

### C40 — REPL error printer treats all `BaseException` as "rot error"

### C41 — No documented `Compiler.execute(program)` for pre-parsed AST

### C42 — `Compiler.run` re-imports `os` at every call

### C43 — `_import_file` is monkey-patched onto `Interpreter`
- **Severity:** style

### C44 — `RotError.__init__` writes prefix into `args[0]` — `e.args` doesn't carry bare message
- **Fix:** override `__str__` instead.

### C45 — `_*Signal` classes subclass `BaseException` — fragile if they escape

### C46 — REPL EOF during continuation silently drops buffered input

### C47 — `_needs_more` doesn't distinguish dict literals from blocks (works incidentally)

### C48 — `--trace` help text inaccurate ("dumps tokenizer/parser tables")

### C49 — No `-V` alias for `--version`

### C50 — `--repl` flag doc says "equivalent" but isn't (C10)

---

## Test coverage gaps

### Modules with little or no test coverage

- **`rot/cli.py`** — NO test file. Argparse, `--no-run`, `--trace`, `--repl`, `.rot` suffix check, file-not-found, exit codes, `--version` all untested.
- **`rot/compiler.py`** — NO test file. Trace output, source_path propagation, colorama, timing display untested.
- **`rot/repl.py`** — Only 4 tests in test_interpreter.py. KeyboardInterrupt, EOF, `_needs_more` edges (strings, comments, mismatched closers), throw-signal escape untested.
- **`rot/errors.py`** — No tests for `line:col:` formatting, `line=0` suppression, class hierarchy.
- **`rot/emitter.py`** — Covers ~6 statement types; try/catch, throw, while, for, break, continue, class, member-assign, index-assign, dict-literal, list-literal, compound-assign, unary `not`, NullLit, BoolLit all unexercised.

### Specific gaps (T1–T122)

**Lexer gaps:** T1 bare CR, T2 tab whitespace, T3 float boundary `3.foo`, T4 number-to-identifier transition, T5 f-string EOF backslash, T6 string EOF backslash, T7 single-char tokens never tested, T8 trace output.

**Parser gaps:** T9 `THIS` bare atom, T10 empty list, T11 keyword as member name, T12 invalid assignment target error, T13 `expected member name after .`, T14 unterminated class body, T15 unknown-infix fall-off, T16/T17/T18 EOF-in-prefix/statement/consume.

**Interpreter gaps:** T19 break/continue-from-function, T20 `_function_depth` across import, T21 cannot-execute fall-through, T22 cannot-evaluate fall-through, T23 unknown binary op, T24 unknown unary op, T25 not-callable, T26 no-member on int/str, T27 no-member on instance, T28 cannot-set-member, T29 unknown-compound-op (×4 sites), T30 IndexAssign on string, T31 dict compound, T32 instance compound, T33 unsupported-escape, T34 cannot-apply detail, T35 REPL uncaught throw.

**Builtin gaps:** T36 input EOF, T37 write_file OSError, T38 range arity, T39 append non-list, T40 pop non-list / with index, T41 min/max no args, T42 mixed-type elements, T43 num failure, T44 is_func variants, T45 assert default message, T46 round with ndigits, T47 stringify of list/dict, T48 stringify of RotInstance.

**Other interpreter gaps:** T49 cout/coutln multi-arg formatting, T50 empty f-string, T51 static-only f-string with escapes, T52 call inside f-string, T53 method call inside f-string, T54 nested f-string, T55 deep-closure mutation (>2 levels), T56 recursive function direct, T57 mutually-recursive functions, T58 empty class construction, T59 class field-only access, T60 multiple instances independence (3+), T61 negative list index, T62 list OOR read, T63 dict missing key read, T64 dict non-string keys, T65 dict mixed-type keys, T66 nested dict, T67 string slicing (should fail), T68 list equality, T69 dict equality, T70 instance equality.

**Try/catch gaps:** T71 wrapped IndexError catch, T72 Python exception stringification, T73 nested try/catch, T74 try without catch (parser), T75 throw outside try, T76 throw across functions caught at top, T77 absolute import path, T78 import without source_dir, T79 import cycle, T80 deep imports, T81 import preserves source_dir on error.

**CLI gaps:** T82 `--no-run`, T83 `--trace`, T84 `--version`, T85 `--repl`, T86 non-`.rot` extension, T87 file not found, T88 RotError → stderr + exit 1, T89 default REPL, T90 trace output, T91 source_path=None.

**REPL gaps:** T92 strings with braces, T93 comments with braces, T94 KeyboardInterrupt mid-input, T95 ctrl-D exit, T96 whitespace-only input, T97 null-result not echoed, T98 multi-statement no-echo.

**Emitter gaps:** T99 try/catch/throw/while/for/break/continue/class/member-assign/index-assign/dict/list/compound/unary-not/Null/Bool unexercised, T100 NotImplementedError fall-through, T101 init → `__init__` rename.

**Edge cases:** T102 empty source, T103 only comments, T104 only whitespace, T105 single expression as whole source.

**v2.13.0 fix gaps:** T106 BoundMethod (regular method) param doesn't clobber outer, T107 BoundMethod `this` doesn't clobber outer, T108 BoundMethod wrong arity error.

**Concatenation gaps:** T109 bool/null + string, T110 list + string.

**Stringification gaps:** T111 lexer trace=True, T112 BoundMethod/RotFunction/RotClass direct print.

**Misc:** T113 compound assign `and=`/`or=` (should fail), T114 truthiness of `[]`/`{}`/`0`/`""`, T115 method-as-value via member access, T116 break/continue across function boundary, T117 compound assign on undefined name, T118 top-level return from imported module, T119 stored BoundMethod call, T120 cout() with no args, T121 coutln() with no args, T122 multiple-arg coutln separator.

---

## Closing notes

- **Total findings:** ~600 across all layers.
- **Stable IDs:** every finding has a unique ID. Reference them when triaging.
- **Auditor reports:** the original per-layer reports are still available via the spawned agents — each agent's `agentId` was logged and can be resumed via SendMessage for follow-ups.
- **Methodology:** seven parallel `general-purpose` agents, each reading every relevant source file and the matching test file. Cross-references between layers were preserved (e.g. emitter findings cite interpreter behavior; CLI findings cite REPL state).
- **Caveats:** a handful of findings are flagged "suspect" where the auditor couldn't fully verify without running the code (e.g. precedence interactions). Treat those as triage candidates, not confirmed bugs.

Most actionable single change: **wrap `Interpreter._evaluate_call` (interpreter.py:477-484) in try/except** — it cascades into fixing ~15 builtin error-leak findings (I7, I9, I10, B4-B9, B14-B16, B21-B22, B26, B29) at once.
