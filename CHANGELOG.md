# Changelog

All notable changes to ROT are documented here. The project follows [Semantic Versioning](https://semver.org/).

## v2.25.3 — imports: cycle no longer re-runs main file body (I40)

### Fixed
- An import cycle `a → b → a` used to re-run the main file's body during the imported module's import (b's `import "a"` saw a's path missing from `_loaded_modules` because `Compiler.run` executed main BEFORE registering its path). Output looked like `a loaded\nb loaded\na loaded`. Fix: `Compiler.run` now seeds `_loaded_modules` with the main file's absolute path before executing it (same path key `_import_file` uses). Cycle imports of main now short-circuit out of the cache and main runs exactly once. Pre-import bindings remain visible to the cycle (b can read `a`'s globals set before main's `import "b"` line). Tests: existing `test_import_cycle_does_not_re_run_main` updated to pin the fix; new `test_import_cycle_main_seeded_before_body_so_binding_uses_partial` confirms partial-binding visibility.

## v2.25.2 — REPL: suppress null-echo on side-effect calls (v2.19.7 follow-up)

### Fixed
- The v2.19.7 always-echo REPL behavior made `coutln("foo")` at the prompt print `foo` from the side effect, then echo `null` (coutln's return value) on the next line. Confusing double output. Fix: in `rot/repl.py::_execute_with_echo`, when the single expression is a `Call` and its evaluated result is `None`, skip the echo. This generalizes to user-defined void functions too (`funct beep() { coutln("beep") }` then `beep()` no longer dumps a trailing `null`). Bare `null` literals and variables bound to null still echo `null` — the suppression is Call-specific. Tests: 5 new in `tests/test_repl.py` (`test_repl_coutln_call_does_not_echo_null`, `test_repl_cout_call_does_not_echo_null`, `test_repl_user_void_function_does_not_echo_null`, `test_repl_call_with_non_null_return_still_echoes`, `test_repl_bare_null_literal_still_echoes`).

## v2.25.1 — parser: `return f"..."` now works (P91)

### Fixed
- `FSTRING` was missing from `_EXPR_STARTS` in `rot/syntax.py`, so `return f"hello"` parsed as a bare `return` (with `None` value) followed by an orphan f-string expression statement. The function returned `null` and the f-string was a no-op. Added `FSTRING` to the set; `return f"..."` now correctly returns the interpolated string. Tests: `tests/test_interpreter.py::test_return_fstring_works`, `test_return_fstring_with_interpolation`.

## v2.24.8 — test backfill: imports + edge cases (T77-T81, T102-T105)

### Added
- 5 tests appended to `tests/test_interpreter.py`. Empty source, comment-only source, and whitespace-only source all parse + interpret without error and produce no output. Deep import chains (A → B → C) flow bindings up through the shared global env — A reads what B defined from C. The import-cycle case (`a → b → a`) pins ACTUAL behavior: the cycle does NOT raise an error today, but because `Compiler.run` does not add the main file's path to `_loaded_modules` before executing it, the cycle re-runs the main file's body during the imported module's import — producing interleaved output `a loaded \n b loaded \n a loaded`. This is the bug-audit's I40 / T79 footgun; the test pins what happens until a future minor fixes it.

## v2.24.7 — test backfill: indexing & dict reads (T61-T66)

### Added
- 6 tests appended to `tests/test_interpreter.py`. Negative list indexing reads from the end (`xs[-1]` is the last element); a negative-index OOR raises a clean `InterpreterError` ("index error: list index out of range") — complements the pre-existing positive-OOR test. Missing-dict-key reads raise an `InterpreterError` whose message mentions both `dict` and `key 'X'` (v2.17.5 phrasing). Dicts with numeric or boolean keys work (pinned separately because Python's `bool <: int` makes `{1: "a", true: "b"}` a footgun — the tests stick to one type at a time). Nested `d["a"]["b"]` dict access works.

## v2.24.6 — test backfill: collection equality (T68-T70)

### Added
- 5 tests appended to `tests/test_interpreter.py`. List `==` is element-wise (Python-default): same elements true, same length but different element false, different length false, empty-vs-empty true. Recursion into nested lists is verified. Dict `==` is key-value based regardless of insertion order. Instance `==` is identity-based: two freshly constructed instances of the same class with identical fields are NOT equal (a separate identity test pins this), while an instance always equals itself; `!=` is the consistent logical complement.

## v2.24.5 — test backfill: closure / recursion (T55-T57, T70)

### Added
- 4 tests appended to `tests/test_interpreter.py`. Three-level closure mutation pins that the chain-walking `set` from v2.10.0 still reaches an outer variable through two layers of nested `funct`. A direct factorial unit test pins recursion at the interpreter level (the `examples/factorial.rot` golden file does end-to-end coverage, but no fast unit test did). Mutual recursion between `even` and `odd` succeeds — pinned as documentation of the env-by-reference closure capture (the lookup of `odd` inside `even` resolves at call time, by which point `odd` is bound in the shared global env). And closures over a for-loop variable observe the final value of the loop var (`3, 3, 3` for `[1 | 2 | 3]`) — the Python late-binding footgun ROT inherits, pinned so a future change to capture-by-value is a conscious decision.

## v2.24.4 — test backfill: BoundMethod fix (T106-T108)

### Added
- 3 tests appended to `tests/test_interpreter.py` covering the regular-method side of v2.13.0's `BoundMethod.call` fix. The pre-existing tests `test_method_param_does_not_clobber_outer_scope` and `test_this_in_method_does_not_clobber_outer_this` exercised the `init` method only — same code path, different lexical site. The new tests pin: (1) a non-init method param assigned via `set_local` does not chain-walk-mutate an outer same-named variable, (2) the `this` binding inside a non-init method does not clobber an outer `this`, and (3) a wrong-arity call on a method raises an InterpreterError whose message names it a "method" (not "function") — distinguishing `BoundMethod.call` from `RotFunction.call`.

## v2.24.3 — test backfill: REPL gaps (T92-T98)

### Added
- 5 new tests appended to `tests/test_repl.py`: a lex-error input (`;`) does not crash the REPL — the error lands on stderr and the next input still executes; pure-empty / whitespace-only input is silently ignored (no echo, no error, no "discarded incomplete input" warning); state is preserved across inputs (`x = 5` then `x` echoes `5`); the `ROT_HISTORY_FILE` env var is honored at runtime by `_install_persistent_history`; and `_install_persistent_history` is a no-op when `readline` is unavailable (simulated by patching `_HAS_READLINE` to `False` — covers the Windows path).

## v2.24.2 — test backfill: Compiler

### Added
- `tests/test_compiler.py` (9 tests). Drives `Compiler` directly (no subprocess) and pins behavior the v2.13.0 audit flagged as untested for the orchestrator module: `parse(source)` returns a `Program` (including empty-source = empty body); `trace=True` prints the three `Process N` stage headers and per-token rows to stdout, while `trace=False` is silent except for the program's own output; `run(source, source_path=...)` resolves relative imports against that file's directory; without a `source_path`, imports resolve against `os.getcwd()`; reusing a single `Compiler` across multiple `run()` calls creates a fresh `Interpreter` each time (user bindings from the first run are gone in the second), and the v2.16.5 frozen-builtins layer keeps rejecting reassignment on every run; and a `RecursionError` raised during parse converts cleanly to `ParserError("expression too deeply nested")` (v2.14.10).

## v2.24.1 — test backfill: CLI

### Added
- `tests/test_cli.py` (10 tests). Drives `python -m rot` via subprocess to cover the gaps identified by the v2.13.0 bug audit (T82-T89): `--version` prints `rot <__version__>`, missing-file exits non-zero with the path in stderr, non-`.rot` extension is rejected, `--no-run` validates without running, `--trace` emits the tokenizer/parser headers and token kinds, a RotError in source exits 1 with the v2.22.7 rustc-style block on stderr, the default (no-file) and explicit `--repl` modes both start the REPL and exit cleanly on EOF, PermissionError on a 0o000 source file produces a clean error (v2.14.8 — skipped on Windows), and a UTF-8 BOM at the start of a source file is silently accepted (v2.20.5).

## v2.23.0 — remove the standalone emitter

### Removed
- `rot/emitter.py` and `tests/test_emitter.py`.

### Rationale
The emitter was an AST → Python source translator that hadn't been on the
active compile path since v2.0.0. The v2.13.0 review and the comprehensive
v2.13.0 bug audit cataloged 40 drift items (`E1`-`E40`): null/true/false
mistranslation, `+`-coercion failure, `this` not renamed to `self`,
`assert(cond, msg)` silently becoming an always-truthy tuple, the v2.10.0
closure-mutation feature missing the required `nonlocal` declarations, and
more. With the bytecode-VM direction being the next strategic step, the
emitter was dead weight.

### Updated
- `rot/ast.py`, `rot/compiler.py`, `rot/keywords.py`, `ARCHITECTURE.md` —
  docstrings and prose reference an emitter no longer.
- `ARCHITECTURE.md` — removed the "Emitter side-path" section and the
  emitter row in the modules table.

### Notes
- No interpreter or parser behavior changed.
- Existing test count drops by 9 (the emitter unit tests).

## v2.22.7 — rustc-style source-line + caret error rendering

### Added
- `RotError.format(source, filename)` in `rot/errors.py`. Renders a rustc-style block when the error has a location:

      error: name 'undef' is not defined
       --> bad.rot:3:6
        |
      3 | cout(undef)
        |      ^

  Falls back to `error: <message>` when `line == 0` (no location) — preserving the no-source fallback. Source-line is omitted when the `source` argument is empty (early errors before any source is read) or when the line is out of bounds. The line-number gutter pads to the digit width of the line number so multi-line files align cleanly.
- `RotError` now stores the message separately as `self.message` (without the legacy `line N:C:` prefix) so `format()` can re-render without the prefix bleeding into the rustc block. `str(err)` keeps the legacy `line N:C: msg` form for backwards-compat — all existing tests that use `str(err)` continue to work unchanged.
- `rot/cli.py` and `rot/repl.py` now call `err.format(source, filename)` instead of `f"rot error: {err}"`. The CLI uses the user's filename; the REPL uses `<repl>` plus the current input buffer as the source string. Pre-existing CLI tests that only checked exit code / "error" presence in stderr continue to pass; tests that pinned the exact `"rot error: line N:C: msg"` substring would have needed updating but none were doing that.
- New tests: `test_format_renders_rustc_style_block_for_located_error`, `test_format_without_location_returns_bare_message`, `test_format_without_source_emits_header_only`, `test_format_out_of_bounds_line_skips_source_block`, `test_format_aligns_caret_when_line_number_has_multiple_digits`, plus subprocess-based end-to-end tests `test_cli_renders_rustc_style_error_for_syntax_error` and `test_cli_renders_rustc_style_error_for_runtime_error` that drive `python -m rot` against tmp_path-resident `.rot` files and assert the rendered block appears on stderr.

## v2.22.6 — `Environment.get` suggests ROT equivalents for Python-isms

### Added
- `_PYTHON_HINTS` table in `rot/interpreter.py` mapping common Python identifiers (`print`, `println`, `None`, `True`, `False`, `def`, `elif`, `self`) to their ROT equivalents (`cout`, `coutln`, `null`, `true`, `false`, `funct`, `elseif`, `this`). `Environment.get` consults the table on a name miss and, if matched, appends `(did you mean 'X'?)` to the "name 'X' is not defined" message. Non-Python-ism names keep the bare message.
- New tests: `test_undefined_print_hints_at_cout`, `test_undefined_True_hints_at_true`, `test_undefined_None_hints_at_null`, `test_undefined_def_hints_at_funct`, `test_undefined_println_hints_at_coutln`, `test_undefined_self_hints_at_this`, `test_undefined_elif_hints_at_elseif`, `test_undefined_unknown_name_has_no_hint` (regression — plain unknowns must not get the hint suffix).

## v2.22.5 — Friendly token-display names in parser errors

### Added
- `_TOKEN_DISPLAY` table and `_token_display(kind)` helper in `rot/syntax.py`. Maps every token kind to a user-facing display string: punctuation/operators render as quoted glyphs (`L_PAREN` → `"'('"`, `EQ_EQ` → `"'=='"`, `COMMA` → `"'|'"` since `|` is ROT's argument separator), keywords render as quoted keyword (`FUNCTION` → `"'funct'"`, `IF` → `"'if'"`), and broad categories render as plain English (`IDENT` → `"identifier"`, `STRING_LIT` → `"string literal"`, `NUMBER` → `"number"`).
- Updated parser sites that previously leaked raw kinds: `_consume` (`expected L_PAREN, got IDENT` → `expected '(', got identifier`), `_parse_atom`'s "expected expression" branch, `_parse_let_stmt`'s "expected = after let" branches, `_parse_member_tail`'s "expected member name after `.`".
- New tests: `test_consume_error_uses_friendly_display_not_kind`, `test_atom_error_uses_friendly_display`, `test_member_after_dot_uses_friendly_display`.

### Notes
- Pre-existing tests in `test_syntax.py` used `with pytest.raises(ParserError):` without inspecting message contents, so none broke. The `with pytest.raises(ParserError, match="..."):` style was not in use for token-kind substrings, so no test had to be updated.

## v2.22.4 — `ParserError` raises consistently carry line/col

### Added
- New `Parser._eof_pos()` helper in `rot/syntax.py` returns the (line, col) one column past the last consumed token — the natural anchor for "unexpected end of input" / "expected X, got end of input" errors. Falls back to (0, 0) only when the entire token stream is empty.
- Every `raise ParserError(...)` in `rot/syntax.py` that lacked positions now passes them: `_parse_statement` EOF, `_parse_prefix` EOF, `_parse_atom` EOF, `_parse_block` unterminated (points at the unclosed `{`), `_parse_class_def` unterminated class body, and `_consume` EOF. `RecursionError` in `Compiler.parse` now anchors at the first token rather than 0:0.
- New tests: `test_unexpected_eof_in_atom_carries_line_col`, `test_unterminated_block_error_carries_line_col`, `test_expected_token_at_eof_carries_line_col`.

## v2.22.3 — Interpreter threads `line` / `col` into runtime errors

### Added
- `Interpreter._error(node, msg)` and `Interpreter._locate(err, node)` helpers in `rot/interpreter.py`. The first builds (does not raise — caller does `raise self._error(...)`) an `InterpreterError` carrying ``node``'s source position; the second wraps a position-less `InterpreterError` and re-raises with a fresh exception carrying ``node``'s position, leaving inner-positioned errors untouched.
- `_execute_statement` and `_evaluate` are now thin wrappers that catch `InterpreterError` and call `_locate(err, current_node)` on it before re-raising. This covers every raise site reachable from the statement/expression dispatchers — including ones inside `Environment.get` (undefined name), builtin call failures, deep nested raises with no AST node in scope. Inner raises that already carry a position keep theirs (the wrapper short-circuits). Net effect: every runtime error now reports `line N:C:` with the position of the AST node that triggered it, instead of `line 0:0:` (CLI prefix suppressed).
- `_ThrowSignal` carries `line` and `col` of the originating `throw` statement; an uncaught throw at the top level surfaces with the throw's position rather than 0:0.
- New tests: `test_undefined_name_error_reports_line_col`, `test_division_by_zero_error_reports_line_col`, `test_index_out_of_range_error_reports_line_col`, `test_inner_call_position_is_kept_not_clobbered_by_outer` (regression — the locator must NOT overwrite an inner error's location), `test_call_arity_error_reports_line_col`, `test_uncaught_throw_reports_throw_line_col`, `test_member_access_error_inside_method_reports_correct_line`.

### Notes
- The locator preserves the inner position (line != 0) — without that, a `cout(undef_inner)` error would re-raise with the position of the surrounding `cout(...)` rather than the inner `undef_inner`. Drilling-down behavior is preserved.

## v2.22.2 — Parser populates `line` / `col` on every AST node

### Added
- Every `_parse_X` method in `rot/syntax.py` now captures the starting token's `line` and `col` and stamps them onto the constructed AST node. Coverage is exhaustive across statements (`FuncDef`, `IfStmt`, `WhileStmt`, `ForStmt`, `Return`, `TryCatch`, `ThrowStmt`, `ImportStmt`, `LetStmt`, `BreakStmt`, `ContinueStmt`, `ClassDef`, `ExprStmt`, `Assign` / `IndexAssign` / `MemberAssign` via `_make_assign`), expressions (`Identifier`, `NumberLit`, `StringLit`, `BoolLit`, `NullLit`, `Call`, `Index`, `MemberAccess`, `ListLit`, `DictLit`, `UnaryOp`, `BinaryOp`), and supporting nodes (`Block`, `ElifBranch`, `Program`). For `BinaryOp` the position points at the OPERATOR token (so a runtime error like `cannot apply '+' to int and str` resolves to the `+`); for `Call` / `Index` / `MemberAccess` it points at the start of the callee/target so chained `obj.x.y` and `foo(...)` resolve to the source `obj` and `foo`. F-string-desugared chains share the f-string's position.
- New tests: `test_parser_populates_line_col_on_call_stmt`, `test_parser_populates_line_col_on_identifier`, `test_parser_populates_line_col_across_lines`, `test_parser_populates_line_col_on_number_literal`, `test_parser_populates_line_col_on_function_def`, `test_parser_populates_line_col_on_binary_op_at_operator`.

### Changed
- All existing AST-shape tests in `tests/test_syntax.py` now run their parsed result through a small `_strip_pos` helper before comparing against the literal-constructed expected AST. The helper recursively zeroes every `line` / `col` field so the shape comparison stays unchanged — pre-existing tests don't assert on positions but their equality checks now would fail without the strip. Tests updated: `test_println_call_with_string_literal`, `test_call_with_multiple_number_args`, `test_call_with_no_args`, `test_bare_identifier_is_an_expression_statement`, `test_number_literal_atom`, `test_string_literal_strips_surrounding_quotes`, `test_nested_call_in_args`, `_expr` helper (powers ~12 `_expr(...)`-based tests), `test_binary_op_inside_call_args`, `test_parses_simple_function_def`, `test_parses_function_with_no_params`, `test_parses_simple_if_statement`, `test_parses_if_elseif_else_chain`, `test_assignment_produces_assign_node`, `test_assignment_value_can_be_a_complex_expression`, `test_return_with_expression`, `test_parses_while_statement`, `test_compound_assign_carries_op`, `test_full_example_functions_rot_parses_end_to_end`, `test_let_statement_parses_to_LetStmt`, `test_let_with_complex_expression`.

## v2.22.1 — AST nodes carry `line` / `col` (schema change, no behavior change)

### Added
- Every dataclass node in `rot/ast.py` now has optional `line: int = 0` and `col: int = 0` fields, defaulting to 0 (= unknown source position). The defaults preserve the existing constructor surface — no parser site has been updated to populate them yet, so this release is a pure schema change. The fields are appended AFTER any existing fields with defaults so positional construction still works (`ast.Identifier("foo")`, `ast.NumberLit(10)`, etc.). Python 3.9 is supported, so `kw_only=True` was NOT used. Tests: `test_ast_nodes_default_line_col_to_zero` verifies the defaults.

## v2.21.6 — `_stringify_instance` cycle protection (stabilization)

### Fixed
- **B2 follow-up**: a `to_string()` method that re-stringified its own instance (`return "X(" + str(this) + ")"`, by accident or by design) used to recurse until Python's recursion limit kicked in, producing several hundred levels of nested `X(X(X(...` output before the inner `RecursionError` was caught by the `except Exception:` fallback. `_stringify_instance` now tracks instances currently being rendered in a module-level `_ACTIVE_INSTANCE_IDS` set (try/finally-scoped, matching the `_seen` pattern for list/dict cycles): re-entry on the same instance short-circuits to `<instance of {ClassName}>` immediately. Sibling renders of the same instance still work — the id is discarded on the way back up. Indirect cycles (instance → list → instance) are also caught because list-cycle detection (B61) and instance-cycle detection together bracket every recursive path through `_stringify`. Tests: `test_to_string_recursive_self_reference_bottoms_out`, `test_to_string_cycle_protection_does_not_break_sibling_renders`, `test_to_string_indirect_cycle_via_field_is_caught`, `test_to_string_separate_instances_with_same_class_each_render`.

### Notes
- v2.21.1-5 introduced rot-style list/dict rendering, instance display with `to_string()`, and the new shapes for functions/classes/bound methods. No pre-existing tests broke during the stability check — the changes flowed through `_stringify` cleanly without colliding with any locked-down output. All 461 tests pass (436 → 461 across the v2.21.x sweep). Examples (`examples/*.rot` vs `examples/*.expected`) still match byte-for-byte.
- Follow-up: REPL echo prints both the function's printed output AND the auto-echoed return value, so `coutln([1])` shows `[1]` then `null`. Pre-existing v2.19.7 design tradeoff for consistent echo semantics; not addressed here. (Left as a separate item — see HANDOFF.)
- Follow-up: `return f"..."` returns `null` because the parser's `_EXPR_STARTS` set doesn't include `FSTRING`. A bare `return` lexes, then the f-string becomes a separate `ExprStmt`. Not addressed here. (Left as a separate item.)

## v2.21.5 — `RotFunction` / `RotClass` / `BoundMethod` __str__

### Fixed
- **B3/I21**: `coutln(f)` for a user function, `coutln(MyClass)` for a class, and `coutln(instance.method)` for a bound method all used to leak Python's internal repr — `<rot.interpreter.RotFunction object at 0x...>`, `<rot.interpreter.RotClass object at 0x...>`, `<rot.interpreter.BoundMethod object at 0x...>` — every callable in rot was rendering with its Python memory address. `_stringify` now special-cases all three (lazy-imported alongside `RotInstance` to keep `builtins.py` independent at module load): `RotFunction` → `<funct {decl.name}>`, `RotClass` → `<class {name}>`, `BoundMethod` → `<method {instance.cls.name}.{decl.name}>`. No override hook for these — they're not user data, the names are already in the source. Affects all `_stringify` paths (cout/coutln, `str()`, f-strings, list/dict recursion, assert messages). Tests: `test_coutln_function_renders_as_funct_name`, `test_coutln_class_renders_as_class_name`, `test_coutln_bound_method_renders_as_method_class_name`, `test_str_of_function_uses_funct_rendering`, `test_str_of_class_uses_class_rendering`, `test_str_of_bound_method_uses_method_rendering`, `test_fstring_with_function_uses_funct_rendering`, `test_fstring_with_class_uses_class_rendering`, `test_fstring_with_bound_method_uses_method_rendering`, `test_list_of_functions_renders_each_as_funct`, `test_list_of_classes_renders_each_as_class`, `test_builtin_function_not_affected_by_funct_rendering` (regression — builtins are Python callables and don't go through the new branches).

## v2.21.4 — `RotInstance` __str__ + `to_string()` override hook

### Fixed
- **B2/I21**: `coutln(a)` for a bare instance used to leak Python's repr (`<rot.interpreter.RotInstance object at 0x...>`) — internal address-and-type goo bleeding into user output. `_stringify` now special-cases `RotInstance` and renders the default form as `<instance of {ClassName}>`. If the class defines a `to_string()` method, `_stringify_instance` invokes it (zero args) and uses the returned string instead — gives users an override hook for instance display that mirrors Python's `__str__`. If `to_string()` raises, returns a non-string, or has the wrong arity, the renderer falls back to the default form silently (display must not crash output).
- The override path needs an `Interpreter` to dispatch the bound method, but `_stringify` is reached from many call sites (cout/coutln, `str()`, f-strings, `assert`) that don't thread an interpreter through. Solution: a module-level `_ACTIVE_INTERPRETER` slot in `builtins.py`, set by `Interpreter.__init__` and `Interpreter.execute` via `_set_active_interpreter`. Last-interpreter-wins; tests construct fresh `Interpreter`s per call and end-user programs only have one interpreter alive at a time, so the simple global is sound. If no interpreter is registered (extreme edge — direct `_stringify` call before any `Interpreter` exists), the override is skipped and the default form is used. Tests: `test_coutln_instance_default_renders_as_instance_of_class`, `test_coutln_instance_to_string_override_is_used`, `test_coutln_instance_to_string_raising_falls_back_to_default`, `test_coutln_instance_to_string_returning_non_string_falls_back`, `test_str_of_instance_uses_to_string_override`, `test_fstring_of_instance_uses_to_string_override`, `test_stringify_instance_with_no_active_interpreter_falls_back`, `test_stringify_instance_inside_list_uses_override`, `test_stringify_instance_inside_dict_uses_override`.

## v2.21.3 — `_stringify` cycle detection for lists and dicts

### Fixed
- **B61**: a self-referential list (`a = []; append(a | a)`) used to render as Python's `[..., [...]]` — Python's `str()` has its own cycle hack, but the output mixed Python style with rot style after v2.21.1/2. `_stringify` now owns the cycle marker: an internal `_seen` id() set tracks lists and dicts on the recursion stack; a value seen twice renders as `[...]` (list) or `{...}` (dict). The set uses try/finally to remove ids on the way back up, so sharing the same list at two sibling positions (not a cycle) still renders the value at each position. Tests: `test_stringify_self_referential_list_does_not_recurse`, `test_stringify_self_referential_dict_does_not_recurse`, `test_stringify_indirect_list_cycle_does_not_recurse`, `test_stringify_indirect_dict_cycle_does_not_recurse`, `test_stringify_two_separate_lists_are_not_a_cycle`, `test_coutln_self_referential_list_does_not_hang`.

## v2.21.2 — `_stringify` renders dicts in rot style

### Fixed
- **B1 (dicts)**: `coutln({"a": 1 | "b": true})` used to print `{'a': 1, 'b': True}` — Python's `str(dict)` was leaking through `_stringify`. `_stringify` now recurses into dicts, joining entries with rot's `|` separator and rendering string keys with double quotes (matching rot literal syntax). Non-string keys are stringified recursively, so booleans/null inside dicts also render rot-style. New helper `_stringify_key` handles the string-key quoting. Tests: `test_stringify_empty_dict_renders_as_braces`, `test_stringify_dict_with_string_keys`, `test_stringify_dict_uses_pipe_separator`, `test_stringify_dict_with_rot_scalar_values`, `test_stringify_dict_with_non_string_keys`, `test_stringify_dict_with_nested_list_value`, `test_stringify_list_of_dicts`, `test_coutln_dict_renders_rot_style`, `test_coutln_dict_with_bool_value`, `test_fstring_dict_uses_rot_style`.

## v2.21.1 — `_stringify` renders lists in rot style

### Fixed
- **B1 (lists)**: `coutln([1 | 2 | true | null])` used to print `[1, 2, True, None]` — Python's `str(list)` was leaking through `_stringify`. `_stringify` now recurses into lists, joining elements with rot's `|` separator and using rot-style scalars (`null`, `true`, `false`) at every depth. Affects `cout`/`coutln`, `str()`, f-string interpolation, `assert` failure messages, and any other path through `_stringify`. Tests: `test_stringify_empty_list_renders_as_brackets`, `test_stringify_list_uses_pipe_separator`, `test_stringify_list_with_rot_scalars`, `test_stringify_nested_lists`, `test_coutln_list_uses_pipe_separator`, `test_coutln_list_with_bool_and_null`, `test_coutln_nested_list`, `test_str_of_list_uses_pipe_separator`, `test_fstring_list_uses_pipe_separator`.

## v2.20.10 — Lexer: hint at `\\` when a trailing `\` consumes the closing quote

### Fixed
- **L8**: `"abc\"` (user wanted a literal trailing backslash) used to error with the bare `unterminated string literal` — confusing, because the user had clearly written a closing quote. The backslash was escaping the `"`, leaving the string unterminated. `_scan_string_literal` now tracks whether the last consumed character was part of a backslash-escape pair; if so, the error message appends ` (did you mean '\\\\'?)` to suggest using a doubled backslash. Tests: `test_trailing_backslash_escapes_closing_quote_gives_hint`, `test_lone_trailing_backslash_no_close_quote_gives_hint`, `test_unterminated_string_without_backslash_has_no_hint` (regression — plain unterminated strings still get the bare message), `test_well_formed_string_with_escaped_quote_still_works` (regression — `"a\"b"` still lexes correctly).

## v2.20.9 — `keywords.py` docstring matches actual identifier rule

### Fixed
- **L57**: the module docstring claimed the lexer "scans a run of lowercase letters", which has been false since v2.6.0 — uppercase was admitted when class names landed (identifier rule `[A-Za-z_][A-Za-z_0-9]*`). Updated to describe the real rule and to note that mixed-case lexemes like `If` correctly classify as `IDENT` since the keyword table is all-lowercase. Also added a one-liner that comments use `//` (C-style), confirming the user's choice to keep `//` over `#`. Tests: `test_keywords_docstring_does_not_claim_lowercase_only`, `test_keywords_docstring_mentions_double_slash_comments`, `test_mixed_case_identifier_is_classified_as_ident` (behavioral regression).

## v2.20.8 — Lexer: type-check `tokenize` input

### Fixed
- **L30**: `Lexer.tokenize(None)` (and `tokenize(42)`, `tokenize(b"...")`, etc.) used to crash with a raw Python `AttributeError: 'NoneType' object has no attribute ...` or `TypeError: 'int' object is not subscriptable` — Python internals leaking through. `tokenize` now type-checks its argument up front and raises `TypeError("Lexer.tokenize requires str, got {type.__name__}")`. Tests: `test_tokenize_with_none_raises_clean_typeerror`, `test_tokenize_with_int_raises_clean_typeerror`, `test_tokenize_with_bytes_raises_clean_typeerror`.

## v2.20.7 — Lexer: trace `_log` uses f-string field widths

### Fixed
- **L34**: `_log` built padding as `" " * (5 - len(str(idx)))` and `" " * (10 - len(repr(token.lexeme)))`, both of which raised `ValueError` on negative repetition counts the moment the index exceeded 99999 tokens or a lexeme's repr exceeded 10 characters. Replaced with `f"{idx:>5} | {token.lexeme!r:<10} | {token.kind}"` so wide values are never a crash. Tests: `test_trace_mode_does_not_crash` (basic format), `test_trace_mode_handles_long_lexeme_without_crashing`.

## v2.20.6 — Lexer: friendly hints for common typos

### Added
- **L18, L20, L25**: a new `_TYPO_HINTS` table maps unexpected-but-common characters to a helpful message body appended to `unexpected character '...'`. Covered: `&` ("ROT does not support bitwise AND; use 'and' for logical AND"), `;` ("ROT does not use ';' to terminate statements; newlines or '}' end statements"), `'` ("ROT only supports double-quoted strings; use \"...\" not '...'"), plus `^`, `~`. Characters not in the table still produce the bare error so the change doesn't mask genuinely unknown input.
- **L21**: `a === b` (and `a !== b`) used to lex as `a == = b` and surface as a downstream parser error. After consuming `==` or `!=`, the lexer now peeks for a trailing `=` and raises `ROT uses '==' for equality, not '==='` (similar for `!==`). Tests: `test_semicolon_gives_friendly_hint`, `test_single_quote_gives_friendly_hint`, `test_ampersand_gives_friendly_hint`, `test_tilde_gives_friendly_hint`, `test_caret_gives_friendly_hint`, `test_triple_equals_gives_friendly_hint`, `test_triple_bang_equals_gives_friendly_hint`, `test_unknown_character_without_hint_still_errors`.

## v2.20.5 — Lexer: silently strip leading UTF-8 BOM

### Fixed
- **L28**: a source file saved with a leading UTF-8 byte-order mark (U+FEFF) used to fail at the first scan with `unexpected character '﻿'`. Many editors on Windows write a BOM by default, so source authored on those tools was unrunnable. `tokenize` now strips a leading BOM before resetting state. Mid-file BOMs are still errors (they're almost certainly a paste artifact). Tests: `test_leading_utf8_bom_is_stripped`, `test_bom_only_at_start_is_stripped_not_in_middle`.

## v2.20.4 — Lexer: f-string with unclosed `{` errors at lex time

### Fixed
- **L5**: `f"hi {x"` (interpolation `{` never closed) used to lex as a valid FSTRING token; the missing `}` then surfaced as a downstream parser error with a less helpful message. `_scan_fstring` now tracks brace depth: the closing `"` is only legal at depth 0, and an EOF or premature `"` with depth > 0 raises `LexerError("unclosed '{' in f-string")`. Tests: `test_fstring_unclosed_interpolation_brace_errors_at_lex_time`, `test_fstring_unclosed_brace_followed_by_eof_errors`, `test_fstring_well_formed_interpolation_still_works` (balanced-braces regression).

### Changed
- `tests/test_interpreter.py::test_fstring_unclosed_brace_errors` previously asserted `ParserError`; updated to assert `LexerError` to reflect the new layering. End-user behavior at the CLI is unchanged (both are `RotError`).

## v2.20.3 — Lexer: trailing `\r` no longer captured in COMMENT lexeme on CRLF

### Fixed
- **L3**: on CRLF (`\r\n`) line endings, a `//` comment lexeme used to include the trailing `\r` (e.g. `"// foo\r"` for `"// foo\r\nbar"`). The same fix as L4 in v2.20.2 — `_scan_comment` now stops on `\n` OR `\r` — also covers this case, but L3 deserves a dedicated regression test. Test: `test_crlf_comment_does_not_capture_trailing_cr`.

## v2.20.2 — Lexer: bare CR (`\r`) handling

### Fixed
- **L2**: a bare carriage return (old-Mac line ending, `\r` not followed by `\n`) did not advance `self.line`. `_advance()` only bumps `self.line` on `\n`, and the `\r` branch in `_scan_token` only consumed an additional `\n` if one followed — so `"\ra\rb"` left every token on line 1 with monotonically increasing columns. The `\r` branch now manually does `self.line += 1; self.col = 1` when no `\n` follows. Test: `test_bare_cr_advances_line`, `test_crlf_advances_line_once` (regression for CRLF case).
- **L4**: a `//` comment on a line ending with bare `\r` (no `\n`) used to consume the rest of the file. `_scan_comment` stopped only on `\n`. It now stops on either `\n` or `\r`, so CR-only line endings no longer cause a single COMMENT token to swallow everything after. Test: `test_comment_with_bare_cr_stops_at_cr`.

## v2.20.1 — Lexer: reset state between `tokenize()` calls, return fresh list

### Fixed
- **L1**: `Lexer.tokenize()` did not reset internal state, so re-using a `Lexer` instance silently returned the previous call's tokens. After the first call, `self.pos` was past the end of the new source and `while not self._at_end()` exited immediately. `tokenize` now resets `self.source`, `self.pos`, `self.line`, `self.col`, and `self.tokens` at the top of every call. Tests: `test_lexer_reuse_returns_correct_tokens_on_second_call`, `test_lexer_reuse_resets_position_tracking`.
- **L60**: `tokenize()` returned a direct reference to the lexer's internal `tokens` list, so a caller that mutated the result also mutated lexer state. Now returns `list(self.tokens)` — a shallow copy. Test: `test_tokenize_returns_fresh_list_not_internal_reference`.

## v2.19.7 — REPL echo: quote strings, always show null

### Fixed
- **C15**: typing `""` (empty string) at the REPL used to echo a blank line — visually indistinguishable from a no-op. Strings are now echoed with surrounding quotes and rot's standard escape sequences for `\`, `"`, `\n`, `\t`, `\r`, so `""` displays as `""` and `"a\nb"` displays as `"a\nb"` (the embedded newline is re-escaped).
- **C16**: typing `null` at the REPL used to be silently suppressed — the user got nothing back, which was confusing. `null` (and any expression that evaluates to null) now echoes `null`. Side effect: function calls that return null (like `coutln("foo")`) now also echo `null` after their printed output; this is the tradeoff for consistent echo semantics.
- New helper `_repl_repr` formats values for echo: strings use the rot-styled quote-and-escape format above, `None` becomes `"null"`, everything else falls through to `_stringify` (which already handles booleans and numbers in rot style). Tests: `test_repl_empty_string_echoes_with_quotes`, `test_repl_non_empty_string_echoes_with_quotes`, `test_repl_string_with_newline_escape_displays_escape`, `test_repl_string_with_inner_quote_displays_escape`, `test_repl_null_literal_echoes_null`, `test_repl_variable_bound_to_null_echoes_null`, plus six unit tests on `_repl_repr` directly.

## v2.19.6 — REPL warns on EOF with buffered input

### Fixed
- **C46**: hitting ctrl-D (EOF) during a multi-line continuation used to silently discard whatever was already in the buffer — the user got no indication their half-typed function or open string was lost. The REPL now prints `discarded incomplete input` to stderr (in addition to the usual newline) when EOF arrives with `buffer` non-empty. EOF at the main prompt with an empty buffer still exits cleanly with no warning. Tests: `test_repl_eof_with_empty_buffer_exits_silently`, `test_repl_eof_during_continuation_warns`, `test_repl_eof_during_unterminated_string_warns`.

## v2.19.5 — Persistent REPL history across sessions

### Added
- **C24**: the REPL now reads from and writes to `~/.rot_history`, so arrow-up across REPL sessions surfaces previous commands. On startup `_install_persistent_history` makes the parent directory if needed, calls `readline.read_history_file(...)`, and registers an `atexit` handler for `readline.write_history_file(...)`. All `OSError`/`FileNotFoundError` failures are swallowed silently — a broken history file or read-only home must never prevent the REPL from starting. Skipped entirely if `readline` is unavailable (Windows). The history path can be overridden with the `ROT_HISTORY_FILE` env var (empty string disables history; tests use this to avoid touching the user's real history file). Tests: `test_repl_history_file_path_uses_home`, `test_repl_install_persistent_history_does_not_crash`, `test_repl_install_persistent_history_skips_if_disabled`, `test_repl_install_persistent_history_swallows_unreadable_file`, `test_repl_startup_with_history_does_not_crash`.
- New `tests/conftest.py` with an autouse fixture that sets `ROT_HISTORY_FILE=""` for every test, so test runs never write to the user's home directory.

## v2.19.4 — REPL `exit`, `quit`, `:q` commands

### Added
- **C17**: the REPL now recognizes `exit`, `quit`, and `:q` as session-end commands. Typing any of these (alone on a line, surrounding whitespace OK) at the main prompt exits cleanly. The commands are only honored when the buffer is empty — `exit` inside a multi-line block or string literal is still treated as ordinary input, so it doesn't accidentally end the session in the middle of typing. ctrl-D (EOF) continues to work as before. The welcome banner now lists the new commands. Tests: `test_repl_exit_command_exits_cleanly`, `test_repl_quit_command_exits_cleanly`, `test_repl_colon_q_command_exits_cleanly`, `test_repl_exit_with_surrounding_whitespace_still_exits`, `test_repl_exit_inside_continuation_is_not_an_exit_command`.

## v2.19.3 — REPL no longer swallows KeyboardInterrupt during execute

### Fixed
- **C14**: the REPL's outer execute handler was `except BaseException` — which caught `KeyboardInterrupt` and `SystemExit` as if they were ordinary errors. A user running a runaway loop in the REPL had no way to ctrl-C out: the interrupt was caught, printed as `rot error:`, and the REPL kept running. Narrowed the handler to `except Exception`, so `KeyboardInterrupt` and `SystemExit` (both `BaseException` but not `Exception`) now propagate normally. The control-flow signals (`_ReturnSignal`, `_BreakSignal`, `_ContinueSignal`, `_ThrowSignal`) are also `BaseException` subclasses, but v2.15.x already wraps them into `RotError` at every escape point, so they never reach this handler. Tests: `test_repl_keyboard_interrupt_during_execute_propagates`, `test_repl_system_exit_during_execute_propagates`.

## v2.19.2 — REPL `//` comments no longer confuse the brace counter

### Fixed
- **C13**: `rot> // {` used to wedge the REPL in perma-continuation — `_needs_more` counted the `{` inside the `//` comment as opening a block, so every subsequent line just deepened the buffer with no way to recover. `_needs_more` now skips `//` comment regions: when it sees `//` outside a string, it advances to the next newline (or end of buffer) before resuming the scan. Real `{` after a comment on the same line (`{ // }`) still counts. Tests: `test_repl_needs_more_ignores_open_brace_in_comment`, `test_repl_needs_more_ignores_close_brace_in_comment`, `test_repl_needs_more_only_skips_to_end_of_line_in_comment`, `test_repl_needs_more_handles_comment_after_real_brace`, `test_repl_comment_with_brace_does_not_hang`.

## v2.19.1 — REPL multi-line string and f-string input

### Fixed
- **C11, C12**: `rot> "hello` (unterminated string literal) used to be parsed and errored immediately, making multi-line strings impossible to enter at the REPL. Same for `rot> f"...` (f-strings). `_needs_more` now tracks an in-string state across the buffer: every unescaped `"` toggles `in_string`, and the function returns `True` (request continuation) if a string is still open at end-of-buffer. Braces inside a string are no longer counted toward depth. F-strings use the same toggle because their opening character is also `"`. Tests in `tests/test_repl.py`: `test_repl_unterminated_string_requests_continuation`, `test_repl_unterminated_fstring_requests_continuation`, `test_repl_needs_more_returns_true_for_open_string`, `test_repl_needs_more_returns_false_for_closed_string`, `test_repl_needs_more_handles_escaped_quote_in_string`, `test_repl_needs_more_returns_true_for_open_fstring`, `test_repl_needs_more_ignores_braces_inside_string`, `test_repl_needs_more_ignores_closing_brace_inside_string`.

## v2.18.6 — user-instance type names wrapped to avoid primitive collision

### Fixed
- **B86**: `class int {}; type(int())` used to return `"int"`, indistinguishable from a real primitive int — any code branching on `type(x) == "int"` would conflate the two. `_builtin_type` now wraps a `RotInstance`'s type name in angle brackets: `"<int>"`, `"<Foo>"`, etc. The primitive types (`int`, `float`, `string`, `list`, `dict`, `bool`, `null`, `function`) remain unwrapped, so `<X>` is always visually distinct from any primitive name no matter what the user names their class. Tests: `test_user_class_named_int_does_not_collide_with_primitive_int`, `test_primitive_int_still_reports_int`, `test_user_class_and_primitive_are_distinguishable`, `test_user_class_named_list_does_not_collide_with_primitive_list`.

### Changed
- `tests/test_interpreter.py::test_type_of_class_instance_is_class_name` previously asserted `type(<Foo instance>) == "Foo"` — pinning the buggy unwrapped behavior. Updated to assert `"<Foo>"`. The test now serves as the regression for the wrapped form.

## v2.18.5 — `type()` of dict views reports "list" instead of "dict_keys"

### Fixed
- **I37**: `type({}.keys())` used to return `"dict_keys"` — a Python internal type name leaking through `type()`. Same for `d.values()` (`"dict_values"`) and `d.items()` (`"dict_items"`). `_builtin_type` now detects these three Python view types by class name and reports `"list"` (they're list-like — iterable and len-able, which is how users actually consume them). Real lists, dicts, and other types are unaffected. Tests: `test_type_of_dict_keys_is_list`, `test_type_of_dict_values_is_list`, `test_type_of_dict_items_is_list`, `test_type_of_real_list_still_list`.

## v2.18.4 — reject Python `bytes` returned from method calls

### Fixed
- **I48**: `"abc".encode()` used to return Python `b'abc'` — a foreign bytes value that rot has no type for, leaking through `_evaluate_call` and printing with the Python `b'...'` repr. The Python-callable path in `_evaluate_call` now checks the result; if it's `bytes`, `bytearray`, or `memoryview`, raise `InterpreterError(f"method 'encode' returns Python bytes, which is not a ROT type")`. The error names the method that produced the bytes. String/list/dict methods that return native rot types (strings, lists, dicts, numbers, bools) are unaffected. Tests: `test_string_encode_returns_bytes_is_rejected`, `test_string_encode_with_arg_returns_bytes_is_rejected`, `test_string_methods_returning_strings_still_work`.

## v2.18.3 — BoundMethod attribute access locked down

### Fixed
- **I20 (BoundMethod)**: `a.f.decl`, `a.f.closure`, `a.f.instance` (where `f` is a method on instance `a`) used to leak the FuncDef AST, the closure `Environment`, and the bound `RotInstance` via Python getattr — completing the I20 leak surface from v2.18.2. `BoundMethod` now has its own `get_member` that rejects every name (a bound method is a callable, not a record). The `MemberAccess` branch special-cases `isinstance(target, BoundMethod)` and routes there. Normal `a.f()` invocations still work. Tests: `test_boundmethod_decl_attribute_not_exposed`, `test_boundmethod_closure_attribute_not_exposed`, `test_boundmethod_instance_attribute_not_exposed`, `test_boundmethod_invocation_still_works`.

## v2.18.2 — RotClass attribute access locked down

### Fixed
- **I20 (RotClass)**: `A.methods`, `A.name`, `A.closure`, `A.call` used to leak the underlying Python attributes of the `RotClass` Python object — exposing the FuncDef-AST dict, the closure `Environment`, etc. Even v2.18.1's `_`-prefix filter didn't help: these aren't dunder names. `RotClass` now has its own `get_member` that exposes nothing; the `MemberAccess` branch special-cases `isinstance(target, RotClass)` and routes there. Calls to `MyClass.method` (where `method` is a user-defined method) now give a clear "cannot access method 'method' directly on class A; call it on an instance" error instead of the prior cryptic Python-getattr leak. Unknown names get the same shape of error. Instance method calls (`a.f()`) still work unchanged. Tests: `test_rotclass_methods_attribute_not_exposed`, `test_rotclass_name_attribute_not_exposed`, `test_rotclass_closure_attribute_not_exposed`, `test_rotclass_call_attribute_not_exposed`, `test_rotclass_user_method_via_class_gives_clear_error`, `test_rotclass_instance_method_call_still_works`.

## v2.18.1 — block `_`-prefixed member access on Python passthrough

### Fixed
- **I47**: `"abc".__class__`, `[1].__len__`, `"a".__init__`, etc. used to leak Python internals via the `MemberAccess` getattr fallback in `_evaluate`. Any rot program could pivot from a string or list to Python's class hierarchy, `__bases__`, `__globals__`, etc. The `MemberAccess` evaluation now rejects any member name starting with `_` (covers dunder and private convention) before attempting `getattr`. Errors use `_builtin_type` so users see rot-style type names (`string`, `list`) in the message, not Python's `str`/`list`. Public methods (`.upper()`, `.sort()`, `.count()`, `.keys()`, etc.) still work unchanged. Tests: `test_dunder_class_on_string_raises_interpreter_error`, `test_dunder_len_on_list_raises_interpreter_error`, `test_dunder_init_on_string_raises_interpreter_error`, `test_dunder_member_uses_rot_type_name_in_error`, `test_legitimate_string_method_still_works`, `test_legitimate_list_method_still_works`, `test_legitimate_dict_method_still_works`, `test_single_underscore_private_also_blocked`.

## v2.17.5 — missing dict key says "key 'k' not found in dict"

### Fixed
- **I35**: `d["missing"]` used to produce `index error: 'missing'` — no indication it was a dict lookup, just a generic index error. The `Index` branch in `_evaluate` now splits the `KeyError` handler out: dict targets produce `key 'missing' not found in dict`; `IndexError`/`TypeError` (lists, strings, wrong index types) keep the existing `index error: ...` phrasing. Tests: `test_missing_dict_key_says_key_not_found_in_dict`, `test_list_out_of_range_index_still_says_index_error` (regression pinning lists' existing wording).

## v2.17.4 — clean message for index-assign on a string

### Fixed
- **I34**: `s[0] = "x"` used to produce `index error: 'str' object does not support item assignment` — the Python phrasing leaked through the wrapped `TypeError`. The `IndexAssign` branch now detects `isinstance(target, str)` up front and raises `InterpreterError("strings are immutable in rot")` before the `target[index] = ...` attempt. Compound forms (`s[0] += "x"`) go through the same guard. Tests: `test_index_assign_on_string_says_strings_are_immutable`, `test_compound_index_assign_on_string_says_strings_are_immutable`.

## v2.17.3 — member compound assign wraps Python op errors

### Fixed
- **I4 (member)**: `c.x /= 0`, `c.x -= "a"` used to leak a raw Python `ZeroDivisionError` / `TypeError`. The `MemberAssign` branch for `RotInstance` (the `class` instance case) had no wrapping at all on the `op_fn(current, new_value)` call. The Python-attribute branch (the fallback for non-`RotInstance` targets) wrapped only the `setattr` write, missing the op itself. Both branches now wrap the op call with the same `division by zero` / `cannot apply '<op>' to <T1> and <T2>: <msg>` pattern used in v2.17.1 and v2.17.2. Tests: `test_member_compound_assign_divide_by_zero_on_instance_raises_interpreter_error`, `test_member_compound_assign_type_mismatch_on_instance_raises_interpreter_error`.

## v2.17.2 — index compound assign wraps Python op errors

### Fixed
- **I4**: `xs[0] /= 0`, `xs[0] -= "a"` used to leak a raw Python `ZeroDivisionError` / `TypeError`. The `IndexAssign` compound branch wrapped only the index-access errors (`IndexError`/`KeyError`/`TypeError` on `target[index]`), not the `op_fn(current, new_value)` call. Restructured the branch so the read, op, and write are each wrapped separately: index errors on read/write produce `index error: ...`; op errors produce `division by zero` or `cannot apply '<op>' to <T1> and <T2>: <msg>`, matching v2.17.1's variable-compound wrapping. Tests: `test_index_compound_assign_divide_by_zero_raises_interpreter_error`, `test_index_compound_assign_type_mismatch_raises_interpreter_error`.

## v2.17.1 — variable compound assign wraps Python errors

### Fixed
- **I3, I5, I6**: `x /= 0`, `x %= 0`, `s -= 1`, `null += 1` (and any other variable-target compound assign) used to leak a raw Python `ZeroDivisionError` / `TypeError` because the `Assign` compound branch in `_execute_statement` called `op_fn(current, new_value)` without a try/except. The plain binary-op path (`_evaluate`'s `BinaryOp` branch) has wrapped these since v2.14.1, but the compound-assign path didn't. Now wraps the call in `try/except (ZeroDivisionError, TypeError)` and re-raises as `InterpreterError` with the same `division by zero` / `cannot apply '<op>' to <T1> and <T2>: <msg>` style. Tests: `test_variable_compound_assign_divide_by_zero_raises_interpreter_error`, `test_variable_compound_assign_modulo_by_zero_raises_interpreter_error`, `test_variable_compound_assign_string_minus_int_raises_interpreter_error`, `test_variable_compound_assign_null_plus_int_raises_interpreter_error`.

## v2.16.6 — `let` keyword for opt-in fresh-local binding

### Added
- **I14**: `let name = expr` is a new statement that binds `name` in the CURRENT scope, never walking the parent chain. This is the explicit opt-in for users who want to shadow an outer name (the v2.10.0 closure-mutation feature would otherwise silently mutate the outer binding). Plain `=` (and compound assigns `+=`, etc.) still chain-walk; `let` is the only path that always binds locally for regular user names.
  - New keyword `let` in `rot/keywords.py` (`LET` token kind).
  - New AST node `ast.LetStmt(name, value)`.
  - Parser handling in `rot/syntax.py`: rejects `let obj.x = ...`, `let xs[0] = ...`, `let foo() = ...`, and any non-`=` follow-up — the target must be a bare identifier.
  - Interpreter handling: `LetStmt` calls `env.set_local`, creating a fresh local binding.
  - `let pi = 3.0` is ALLOWED — `let` shadows the frozen builtin in the current scope (the chain is never walked, so the frozen layer is untouched). Plain `pi = 3.0` is still rejected by v2.16.5.
  - `let this = ...` is rejected at parse time (the lexer tokenizes `this` as `THIS`, not `IDENT`).
- Tests: `test_let_creates_fresh_local_binding`, `test_let_inside_function_followed_by_chainwalking_assign`, `test_let_at_top_level_works`, `test_let_can_shadow_builtin`, `test_plain_assign_to_builtin_still_rejected_even_after_let_is_added`, `test_let_rejects_member_target`, `test_let_rejects_index_target`, `test_let_rejects_call_target`, `test_let_requires_equals`, `test_let_cannot_bind_this`, plus parser tests in `test_syntax.py`.

### Breaking
- `let` is now a reserved keyword. Any user file that used `let` as an identifier will break — accepted tradeoff per the design discussion.

## v2.16.5 — builtins live in a frozen env layer

### Fixed
- **I17, B59**: `pi = 3.0`, `cout = "x"`, `len = 99` used to silently succeed — builtins were bound in the same env as user globals, and the chain-walking `set` happily rebound them. Builtins now live in a separate `Environment(frozen=True)` at the root of the env chain. The user's global scope is a fresh child env. Writes that walk up into the frozen layer (whether the name is found there or not) raise `InterpreterError("cannot reassign builtin 'pi'")`. `Environment` gains a `frozen` flag and a `_populate_frozen` escape hatch used only by interpreter init. User-scope `Assign` and `set_local` (params, `this`, for-loop var, declarations from v2.16.1/v2.16.2) work exactly as before. The v2.10.0 closure-mutation feature is unchanged for user-defined names. Tests: `test_reassigning_builtin_pi_is_rejected`, `test_reassigning_builtin_cout_is_rejected`, `test_reassigning_builtin_len_is_rejected`, `test_compound_assign_to_builtin_is_rejected`, `test_non_builtin_assignment_still_works`, `test_assignment_in_function_still_mutates_global` (pins v2.10.0 semantics).

### Changed
- `tests/test_interpreter.py::test_class_with_no_init_takes_no_args` used `e = Empty()` as scaffolding — the variable name `e` clashed with the math constant builtin under the new frozen layer. Renamed to `inst` (incidental rename, not pinning of buggy behavior; the test is about class-with-no-init arity, not name shadowing).

## v2.16.4 — reject reassigning `this` inside a method

### Fixed
- **I22**: inside a method, `this = <expr>` (or `this += 1`, etc.) used to silently mutate the method's local `this` binding (methods bind `this` via `set_local`), breaking the rest of the method body's view of its instance. The `Assign` branch in `_execute_statement` now rejects `stmt.name == "this"` whenever `this` is bound somewhere up the env chain (i.e. we're inside a method). Top-level `this = ...` remains legal — a pre-existing test (`test_this_in_method_does_not_clobber_outer_this`) uses it as scaffolding, and outside of methods `this` is not a reserved name. Tests: `test_reassigning_this_in_method_is_rejected`, `test_reassigning_this_in_compound_assign_is_rejected`, `test_top_level_this_assign_still_legal_for_compat`.

## v2.16.3 — catch variable scoped to the catch block

### Fixed
- **I12, I13**: `try { ... } catch (e) { ... }` used to bind `e` in the enclosing scope via the chain-walking `set`. That silently clobbered any existing outer `e` (notably the math constant `e ~= 2.718`) and leaked the binding past the end of the catch block. Now the catch body runs in a fresh `Environment` whose parent is the current scope: the catch variable is `set_local`'d into that env and disappears when the catch ends. Reads inside the catch still see and chain-walk-mutate outer names (closure mutation untouched). Tests: `test_catch_var_does_not_clobber_outer_binding`, `test_catch_var_does_not_leak_to_enclosing_scope`, `test_catch_var_local_to_catch_body_only`.

## v2.16.2 — nested class declarations bind locally

### Fixed
- **I16**: a nested `class A` inside `funct outer` used to silently overwrite the outer `A` for the same reason `funct` did (I15) — the `ClassDef` branch in `_execute_statement` called the chain-walking `self.env.set(...)`. Class declarations now use `set_local`. Test: `test_nested_class_does_not_clobber_outer_class`.

## v2.16.1 — nested funct declarations bind locally

### Fixed
- **I15**: a nested `funct f` inside `funct outer` used to silently overwrite the outer `f` because `_execute_statement`'s `FuncDef` branch called `self.env.set(...)`, which chain-walks (v2.10.0 closure-mutation semantics) and so found the outer `f` and rebound it. Function declarations now always use `set_local`, introducing a fresh binding in the current scope. Only user `Assign` (`x = ...`) walks the chain. Test: `test_nested_funct_does_not_clobber_outer_funct`.

## v2.15.2 — uncaught throw raises a clean InterpreterError

### Fixed
- **I44, C5**: an uncaught `throw` (at top level, or inside a function with no surrounding `try`/`catch`) used to escape as a raw `_ThrowSignal` (a `BaseException`) and print a Python traceback. `Interpreter.execute` now wraps the outer statement loop in `try/except _ThrowSignal` and re-raises as `InterpreterError("uncaught throw: <value>")`. Catches of throws inside a matching `try`/`catch` still work — the wrapper only fires when the signal escapes the entire program.

## v2.15.1 — break/continue can no longer escape a function boundary

### Fixed
- **I1, I2**: `break` or `continue` inside a function called from a loop used to silently bail the caller's loop, because `_loop_depth` was interpreter-global. `RotFunction.call` and `BoundMethod.call` now save and zero out `_loop_depth` on entry and restore it in `finally`, so loops outside the function body don't count. They also catch any `_BreakSignal` / `_ContinueSignal` that escapes the function body and re-raise as `InterpreterError("\`break\` outside of a loop")` / `InterpreterError("\`continue\` outside of a loop")` — matching the existing top-level message so error-text assertions stay green. Lexically valid `break` / `continue` (inside a loop inside the function) still work.

## v2.14.12 — regression test pins UTF-8 on every file-open site

### Fixed
- **C18, C19**: every `open()` / `read_text()` / `write_text()` in `rot/*` was already updated to use `encoding="utf-8"` by v2.14.6, v2.14.9, and v2.14.11. This release adds a regression test (`test_all_file_open_sites_use_explicit_utf8`) that scans the package and fails if a future change reintroduces a locale-dependent open. No code change here — the test is the deliverable.

## v2.14.11 — _import_file wraps OSError on the imported file

### Fixed
- **C7**: `import "path"` of a file that exists but is unreadable (PermissionError), a directory (IsADirectoryError), or not UTF-8 (UnicodeDecodeError) used to leak a raw Python traceback. The `_import_file` open is now wrapped: each error becomes a rot-prefixed `InterpreterError` (`import 'path': permission denied`, etc.). The import path also gets `encoding="utf-8"` explicitly.

## v2.14.10 — Compiler wraps RecursionError

### Fixed
- **C6**: deeply nested parens (e.g. `((((((1))))))` with 2000+ levels) used to leak a Python `RecursionError` from the parser. `Compiler.parse` now catches `RecursionError` and raises `ParserError("expression too deeply nested")`. `Compiler.run` adds a defensive `RecursionError` -> `InterpreterError("call stack too deep")` net for any interpreter sites not covered by v2.14.2.

## v2.14.9 — CLI reads source as UTF-8 and reports decode errors cleanly

### Fixed
- **C3**: a non-UTF-8 source file used to crash with a Python `UnicodeDecodeError` traceback. The CLI's `source_path.read_text()` now passes `encoding="utf-8"` explicitly and catches `UnicodeDecodeError`, routing it through `parser.error` for a one-line "is not valid UTF-8" message.

## v2.14.8 — CLI catches OSError broadly, not just FileNotFoundError

### Fixed
- **C1, C2**: passing a path that exists but is unreadable (PermissionError) or is a directory (IsADirectoryError) used to leak a raw Python traceback. The CLI's `source_path.read_text()` now catches `IsADirectoryError`, `PermissionError`, and the general `OSError` after the existing `FileNotFoundError` handler, routing each through `argparse.parser.error` for a clean one-line message and exit code 2.

## v2.14.7 — builtin arity errors use rot names, not Python internals

### Fixed
- **B19, B20, B32, B39, B42-B50**: arity errors for `num`, `str`, `type`, `is_num` / `is_str` / `is_list` / `is_dict` / `is_bool` / `is_null` / `is_func`, `read_file`, `write_file`, `rand_int`, `rand_float`, `assert`, `append`, `pop`, `input` used to leak Python's internal underscore-prefixed names (`_num()`, `_stringify()`, `_builtin_type()`, etc.). Every affected builtin now uses `*args` + a shared `_arity(name, args, expected)` helper that produces messages like `num: takes 1 arg, got 0`. Side-effect: `_assert` now uses `_stringify` for the failure message (B52 partial).

### Changed (internal)
- `_num` renamed to `_builtin_num`, the `str` builtin now dispatches through `_builtin_str` wrapper (`_stringify` retained for internal use by `cout`/`coutln`/REPL).

## v2.14.6 — read_file/write_file use explicit UTF-8

### Fixed
- **B33, B34, B35**: `read_file` / `write_file` now open with `encoding="utf-8"` explicitly instead of using the platform-default locale. Non-UTF-8 input raises `InterpreterError("read_file: ... is not valid UTF-8: ...")` instead of leaking a raw `UnicodeDecodeError`; encode failures on write are wrapped likewise. Output files are now portable across platforms.

## v2.14.5 — range validates every arg before int() coercion

### Fixed
- **B28, B29**: `range(0.5 | 3)` and `range("abc")` used to silently truncate floats (`int(0.5) == 0`) or leak Python's `ValueError("invalid literal for int() with base 10: 'abc'")`. Now every range argument is validated as an integer up front via a shared `_range_int` helper. Errors come out as clean rot messages like `range: stop argument must be an integer, got float`.

## v2.14.4 — range step must be an integer, says so

### Fixed
- **B27**: `range(0 | 3 | 0.5)` used to say "step argument must not be zero" because `int(0.5) == 0` happened silently before the zero check. Now the float step is rejected first with "step argument must be an integer, got float". Zero ints still report "must not be zero".

## v2.14.3 — pop reports "out of range" when index, not the list, is the problem

### Fixed
- **B41**: `pop([1] | 5)` used to say "cannot pop from empty list" even though the list wasn't empty. Now indexed pops with a bad index report "pop: index N out of range for list of length M". The bare `pop([])` empty case keeps its existing message.

## v2.14.2 — clean message for runaway recursion

### Fixed
- **I10**: deep recursion in rot user code used to leak a raw Python `RecursionError("maximum recursion depth exceeded while calling a Python object")`. Now `Interpreter._evaluate_call` catches `RecursionError` and re-raises `InterpreterError("call stack too deep")`. Catchable in rot's own `try`/`catch`.

## v2.14.1 — wrap Python exceptions from builtin calls

### Fixed
- **I7, I9, I10, B4-B9, B14-B16, B21-B22, B26, B29** (and many of the related "Python error leaks to the user" findings): `Interpreter._evaluate_call` now wraps `TypeError` / `ValueError` / `ZeroDivisionError` / `UnicodeDecodeError` / `UnicodeEncodeError` / `OSError` raised by any callable (every builtin) into a clean `InterpreterError`. The error name is stripped of its internal leading underscore (e.g. `_num` -> `num`). `InterpreterError`s raised by builtins are not double-wrapped. As a side effect, `len(null)`, `min([])`, `num("abc")`, `abs("x")`, etc. are now catchable in rot's own `try`/`catch`.

## [2.13.0] - 2026-05-26

Bug-fix sweep driven by a code review. Every fix has a regression test.

### Fixed — Python exceptions now consistently wrap as `InterpreterError` (catchable in `try`/`catch`)
- **Binary op type errors** (`1 - "x"`) — wrapped with a "cannot apply X to A and B" message.
- **Division and modulo by zero** (`1 / 0`, `5 % 0`) — wrapped as "division by zero".
- **Unary minus on non-numeric** (`-"x"`) — wrapped as "cannot negate string".
- **Index errors on both read and write** (`xs[5] = 1`, `dict[missing]`) — wrapped with the underlying message.
- **`for` over non-iterable** (`for x in 123 { }`) — wrapped as "cannot iterate over int".
- **`pop` on empty list** — wrapped.
- **`range(a, b, 0)`** — wrapped (was raw Python `ValueError`).
- **`rand_int(5, 1)`** — validates `low <= high`.
- **`read_file` / `write_file` OSError** — wrapped.
- **`sqrt(negative)`** — wrapped.

### Fixed — control-flow errors
- **`break` / `continue` at top level** — used to escape as `BaseException` with a Python traceback. Now raise `InterpreterError("break outside of a loop")` etc. Tracked via `Interpreter._loop_depth` / `_function_depth`.
- **`return` at top level** — same fix.

### Fixed — method scoping bug (real impact!)
- `BoundMethod.call` was using `local.set("this", instance)` and `local.set(param, value)`. After v2.10.0's chain-walking `set`, this meant a method whose param name matched an outer-scope variable would *mutate the outer variable*. Same for `this` if an outer `this` existed. Both now use `set_local` correctly. Test: `test_method_param_does_not_clobber_outer_scope`.

### Fixed — lexer/parser fragility
- **CRLF (`\r\n`) line endings** — used to crash on the `\r`. Now correctly produce one NEWLINE token. (Test: `test_crlf_line_endings_work`.)
- **F-string with garbage in `{}`** (`f"{1 2}"`) — the inner parser silently dropped trailing tokens. Now raises `ParserError`.
- **Member access with keyword names** (`obj.class`, `dict.if`) — used to fail (keywords aren't IDENT). Now allowed.
- **`SINGLE_QUOTE` token dropped** — was lexed as a token but the parser never consumed it. Now `'` is a normal unrecognized character.

### Tests
- 20 new tests, all assertions of `InterpreterError` or `ParserError` on the previously-leaking paths.
- Total: **201 passing** (181 → 201, +20).

### Design choices reaffirmed (not bugs)
- `Environment.set` walking the parent chain is the v2.10.0 feature, not a bug — closure mutation is intentional.
- For-loop variable always binds locally (via `set_local`) — intentional asymmetry to keep loops from leaking state.

## [2.12.0] - 2026-05-26

### Added
- **REPL** in `rot/repl.py`. Invocation: `python -m rot` (no file) or `python -m rot --repl`.
- Features:
  - Bare expressions echo their non-null value (Python-REPL style). Statements execute silently.
  - **Multi-line input**: heuristic counts `{ [ (` outside strings; if unbalanced, prompt continues with `...` until balanced.
  - **Persistent state**: a single `Interpreter` lives for the whole session. Variables and functions persist across inputs.
  - **Errors don't kill the session**: caught and printed, prompt continues.
  - **readline integration** (Unix): arrow keys, line editing, history work out of the box.
- CLI: `file` argument is now optional. Omitting it (or passing `--repl`) starts the REPL.

## [2.11.0] - 2026-05-26

### Added
- **`import "path"`**: loads a `.rot` file and executes its top-level statements in the current scope. Function and class definitions become available to the importing file.
- **Path resolution**: paths starting with `/` are absolute; otherwise relative to the directory of the importing file. `.rot` extension is appended automatically if missing.
- **Cached**: importing the same file twice runs it once. Prevents both wasted work and circular-import infinite loops.
- `Interpreter.set_source_dir(path)` + `_source_dir` tracking + `_loaded_modules: set[str]` cache.
- `Compiler.run` and CLI now thread `source_path` through so `import "rel/path"` resolves against the right directory.
- New AST node `ImportStmt(path)`, new keyword `import`.

## [2.10.0] - 2026-05-26

### Changed
- **`Environment.set` now walks the parent chain.** If `name` is already bound anywhere up the chain, that binding is mutated. Otherwise a new binding is created in the current scope.
- This makes the **counter-closure idiom work** — `count += 1` inside an inner function now mutates the `count` declared in an enclosing function.
- New `Environment.set_local(name, value)` bypasses the chain walk for cases that must always bind locally: function parameters, `this` inside method calls, `for`-loop iteration variable.
- Trade-off: deliberately shadowing an outer variable by re-using its name no longer works (assignment finds the outer one). Use a different name to shadow, or rely on parameter binding (which is local).

## [2.9.0] - 2026-05-26

### Added
- **F-strings** (Python-style): `f"hello, {name}"`. The lexer recognizes `f"..."` as a single `FSTRING` token; the parser splits the content into static segments and `{expr}` interpolations.
- **No new AST node** — f-strings desugar to a chain of `+` over `StringLit` and `str(expr)` calls. Reuses existing nodes; the interpreter needs no changes.
- Multi-interpolation, expressions inside braces (`f"{1 + 2}"`), escapes in static parts, and clear errors on unclosed/empty `{}`.

### Changed
- **`str()` builtin** now uses the rot-style stringifier (`null`/`true`/`false`). Previously was Python's `str` (which gives `None`/`True`/`False`). This makes `f"{true}"` render as `"true"` consistently.
- `_stringify` helper moved from `rot/interpreter.py` to `rot/builtins.py` so both `cout`/`coutln` (interpreter-internal) and `str` (stdlib) can use the same definition.

## [2.8.0] - 2026-05-26

### Added
- **`rot/builtins.py`** — dedicated module hosting the standard library. Registry `BUILTINS: dict[str, Any]` is iterated at `Interpreter.__init__` to bind everything into the global env.
- **~25 new built-in functions and constants**:
  - I/O: `input(prompt)`, `read_file(path)`, `write_file(path, content)`.
  - Math: `abs`, `min`, `max`, `pow`, `sqrt`, `floor`, `ceil`, `round`, plus constants `pi`, `e`. `min`/`max` accept either a single iterable or multiple args.
  - Type introspection: `type(x)` (returns rot-style names: `"int"`, `"string"`, `"list"`, the class name for instances, etc.), `is_num`, `is_str`, `is_list`, `is_dict`, `is_bool`, `is_null`, `is_func`.
  - Random: `rand_int(a, b)`, `rand_float()`.
  - Assertions: `assert(cond)` / `assert(cond, message)` — raises `InterpreterError` on false (catchable in `try`/`catch`).

### Changed
- Moved existing built-ins (`str`, `num`, `len`, `range`, `append`, `pop`) from `rot/interpreter.py` into `rot/builtins.py` for clean separation.

## [2.7.0] - 2026-05-26

### Added
- **`try { ... } catch (e) { ... }`**: error handling. New `TryCatch(try_block, catch_var, catch_block)` AST node.
- **`throw expr`**: raise any value (string, dict, instance — whatever). New `ThrowStmt(value)` AST node.
- New `_ThrowSignal(BaseException)` carries user-thrown values up to the nearest `try`.
- `catch` clause binds the caught value to the named variable. Catches:
  - `throw`-raised values directly.
  - Python `Exception` subclasses (`InterpreterError`, `ZeroDivisionError`, etc.) — exposed as their `str(e)` representation.
  - Control-flow signals (`return` / `break` / `continue`) are NOT caught — they subclass `BaseException` directly.
- New keywords: `try`, `catch`, `throw`.

## [2.6.0] - 2026-05-26

### Added
- **Classes**: `class Name { method() { ... } init(...) { ... } }`. Methods declared without `funct` keyword.
  - New `ClassDef(name, methods)` AST node.
  - New keywords: `class`, `this`.
  - `init` method is the constructor; called when the class is invoked with `()`. A class with no `init` accepts no args.
  - `this` refers to the current instance inside method bodies.
  - Fields are set via `this.field = value` and read via `this.field`.
  - Method calls (`instance.method()`) return a `BoundMethod` from member access; calling it binds `this`.
- New interpreter types: `RotClass`, `RotInstance`, `BoundMethod`.
- **Uppercase identifiers**: identifier rule extended to `[A-Za-z_][A-Za-z_0-9]*`. Class names conventionally start capitalized (`Point`, `Counter`); this lets `MyClass` and `x1` lex naturally.
- `examples/counter.rot` (Counter with init/inc/show).

### Fixed
- `THIS` token added to `_EXPR_STARTS` so `return this.x` parses as `return <expression>` rather than bare `return` (which would have returned `null`).

## [2.5.0] - 2026-05-26

### Added
- **Member access**: `obj.attr` and `obj.method(args)`. New `MemberAccess(target, member)` AST node. Interpreter uses Python `getattr` — meaning every string/list/dict method ships for free (`s.upper()`, `xs.sort()`, `d.keys()`, `"a,b,c".split(",")`).
- **Member assignment**: `obj.field = value` and `obj.field += 1`. New `MemberAssign(target, member, value, op)` AST node.
- **Dictionaries**: `{key: value | key2: value2}` literal (`|` separator, `:` for key/value). Empty dict `{}` works. New `DictLit(pairs)` AST node. Indexed with `d[key]`, assigned with `d[key] = value`. Iteration yields keys (matches Python semantics).
- New tokens: `DOT` (`.`), `COLON` (`:`).

### Changed
- `_parse_atom_or_call` chains member/index/call in a single loop so `arr[0].foo().bar` works.
- `_make_assign` knows about `MemberAccess` targets — `obj.x = v` desugars to `MemberAssign`.
- `_EXPR_STARTS` includes `L_CURLY` (for dict literals in `return` position etc.). Block parsing is unambiguous because `_parse_block` is only invoked from statement contexts (`funct`, `if`, etc.); a `{` in expression position is always a dict.

## [2.4.0] - 2026-05-26

### Added
- **Lists**: `[1 | 2 | 3]` literal (uses `|` separator to stay consistent with `funct hi(x | y)`). `ListLit(elements)` AST node.
- **Indexing**: `list[i]` for reading, `list[i] = v` for writing, `list[i] += 1` for compound. New `Index(target, index)` and `IndexAssign(target, index, value, op)` AST nodes. Indexing also works on strings (`"hello"[1]` → `"e"`).
- **`for x in iter { ... }`** loop. Iterates over any Python iterable (lists, strings, ranges).
- **`break`** and **`continue`** keywords. Implemented via `_BreakSignal` / `_ContinueSignal` (`BaseException` subclasses) caught by enclosing `for` / `while`.
- **Built-ins**: `range(n)`, `range(start, end)`, `range(start, end, step)`, `append(list, item)`, `pop(list)` / `pop(list, index)`.
- `examples/sum_list.rot` exercising for-loop, compound assign, list literal.

### Changed
- `_parse_statement` refactored. Used to look ahead for `IDENT '='` to detect assignment; now always parses the expression first, then checks for `=` or compound. Cleaner and lets `list[i] = v` work via `_make_assign` converting an `Index` target into `IndexAssign`.
- `_parse_atom_or_call` is now a loop, so `arr[0][1]` and `foo()[0]` chain correctly.
- `_EXPR_STARTS` includes `L_BRACKET` so `return [1, 2, 3]` works.

## [2.3.0] - 2026-05-26

### Added
- **Float literals**: `3.14` lexes as one `NUMBER` token; parser produces `NumberLit(value=3.14)` as a Python float.
- **String escape sequences**: `\n`, `\t`, `\r`, `\0`, `\"`, `\'`, `\\` all decoded by `_decode_string_escapes` in `rot/syntax.py`. Escaped quotes inside strings no longer terminate them.
- **`+` auto-coerces to string**: if either operand is a string, both are stringified (rot-style: `null`, `true`, `false`, lowercase). Lets you write `"count: " + 42`.
- **Compound assignment**: `+=`, `-=`, `*=`, `/=`, `%=`. New two-char tokens `PLUS_EQ` / `MINUS_EQ` / `STAR_EQ` / `SLASH_EQ` / `PERCENT_EQ`. `ast.Assign.op` field carries `"="` for plain or the binary op for compound.

### Changed
- **`cout`/`coutln` print rot-style**: `null` instead of `None`, `true`/`false` instead of `True`/`False`. The output now matches what you'd write in source. Tests updated accordingly.

## [2.2.0] - 2026-05-26

The "you can actually write programs in this" release. **Fizzbuzz runs end-to-end.**

### Added
- **`while` loops**: `while (cond) { body }`. New `WhileStmt(cond, body)` AST node + grammar rule + interpreter handling.
- **Boolean literals**: `true` and `false` (lowercase, ROT-style). New `BoolLit(value)` AST node. Returns Python's `True`/`False`.
- **`null` literal**: New `NullLit()` AST node. Returns Python `None`.
- **Unary operators**:
  - `-x` (numeric negation) — `-5`, `-x`, `-(a + b)` all parse. Binds tightest of any prefix.
  - `not x` (logical not) — Python-style precedence: lower than comparisons (`not a == b` parses as `not (a == b)`), higher than `and`/`or` (`not a or b` parses as `(not a) or b`).
  - New `UnaryOp(op, operand)` AST node.
- **Logical operators**: `and`, `or` as keywords. Short-circuiting (the interpreter handles them specially in `_evaluate`). Return the actual operand value, not just a bool — `true or oops()` returns `True` without calling `oops()`.
- **Modulo operator**: `%`. Same precedence as `*` and `/`.
- **Built-in functions**: `str(x)`, `num(x)`, `len(x)`. Bound in the interpreter's global environment.
- `examples/fizzbuzz.rot` (+ `.expected`) — the canonical "is this language real?" test. **Yes.**
- 19 new tests across lexer / syntax / interpreter.

### Changed
- `_INFIX_PRECEDENCE` table reworked. New layout:
  - 1: `or`
  - 2: `and`
  - 3: reserved for prefix `not`
  - 4: `==`, `!=`
  - 5: `<`, `<=`, `>`, `>=`
  - 6: `+`, `-`
  - 7: `*`, `/`, `%`
  - prefix `-`: tightest (highest)
- `_EXPR_STARTS` expanded to include `TRUE`, `FALSE`, `NULL`, `SUBTRACTION`, `NOT` so bare `return` detection knows what can start an expression.
- Emitter handles all new node types (parens around `UnaryOp` children to preserve precedence).

## [2.1.0] - 2026-05-26

Variable assignment and function return values land — the language stops being a tech demo and becomes something you can write actual programs in. Recursion now works (see `examples/factorial.rot`).

### Added
- `Assign(name, value)` and `Return(value)` AST nodes; `Statement` union expanded.
- `return` reserved word in `KEYWORDS`.
- Grammar rules in `rot/syntax.py`:
  - `return_stmt := 'return' expr?` — bare `return` returns `None`.
  - `assign := IDENT '=' expr` — one-token lookahead distinguishes from a bare-identifier expression statement.
- Interpreter handling:
  - `Assign` calls `env.set(name, value)`.
  - `Return` raises a private `_ReturnSignal(value)` (subclass of `BaseException` so generic `except Exception` blocks don't swallow returns).
  - `RotFunction.call()` catches `_ReturnSignal` and returns its value; falls off the end → `None`.
  - `_evaluate_call()` now propagates the function's return value back to the caller.
- Emitter handles the new statement kinds: `Assign` → `name = value`, `Return` → `return value` (or bare `return`).
- `examples/factorial.rot` (+ `.expected`) — classic recursive factorial showcasing both return values and recursion in one ~5-line program.
- 17 new tests across lexer / syntax / interpreter / emitter for the new features.

### Changed
- **Identifiers may now contain underscores.** `hello_world`, `_private`, and `_` all lex as `IDENT`. Identifier start: lowercase letter or `_`. Continuation: same (digits intentionally still excluded for now). Driven by the fact that without this, function names like `first_positive` from idiomatic real-world code wouldn't lex.

## [2.0.0] - 2026-05-26

**The headline release.** `exec()` is gone. ROT no longer compiles to Python — it runs its own AST through a tree-walking interpreter. This is the defining v1→v2 boundary.

### Added
- `rot/interpreter.py` — a tree-walking interpreter over `ast.Program`:
  - `Environment` for lexically-scoped name bindings (with `parent` chain for closures).
  - `RotFunction` wraps a `FuncDef` with its closure environment. Arity-checks args on call. Sets up a child scope, executes the body, restores the prior env.
  - `Interpreter.execute(program)` walks statements; `_evaluate` dispatches on expression node type; `_BINARY_OPS` table covers `+ - * / < <= > >= == !=`.
  - `cout` and `coutln` are bound as Python callables in the global environment (the only built-ins).
- `InterpreterError` (in `rot/errors.py`) — raised for undefined names, arity mismatches, uncallable values, unknown operators.
- `tests/test_interpreter.py` — 12 tests covering: `cout` vs `coutln` semantics, multi-print concatenation, function definition + call, multi-param funcs (separated by `|`), `if/elif/else` branch selection, Pratt-parsed arithmetic precedence (`1+2*3 == 7`), parenthesized arithmetic, undefined-name error, wrong-arity error, lexical scope (inner function can see outer's `coutln`).

### Changed
- **`Compiler.compile()` removed.** Replaced by:
  - `Compiler.parse(source) -> ast.Program` — lex + parse, returns the AST.
  - `Compiler.run(source) -> None` — parse + interpret. The default path.
- **CLI: `--output` and the `output.py` artifact are gone.** `--no-run` now means "parse and validate, don't execute" (it used to mean "transpile to file but don't run"). Default invocation just interprets.
- `test_end_to_end.py` rewired to use `Compiler.run()` with `redirect_stdout` instead of `Compiler.compile()` + `exec`.
- ARCHITECTURE.md updated for the new pipeline.
- README updated: ROT is now an interpreter, not a transpiler.

### Removed
- `exec()` from the runtime. ROT now interprets the AST directly.
- The `output.py` build artifact (was already gitignored; no longer produced).
- `--output` and `-o` CLI flags.
- `Compiler.save()` and `Compiler.execute()` methods (replaced by the interpreter pipeline).

### Kept around
- `rot/emitter.py` and `tests/test_emitter.py` remain. The emitter is no longer on the active path but still works correctly and is tested; a future `--transpile` flag could rewire it.

## [1.9.0] - 2026-05-26

The AST takes over the active compile path. The v1 transpiler is gone. End-user behavior is unchanged — `examples/functions.rot` still prints `same` — but the entire pipeline now goes `tokens → AST → Python → exec` instead of `tokens → Python → exec`.

### Added
- `rot/emitter.py` — AST → Python source emitter. Walks `ast.Program` and produces Python with correct indentation and precedence-preserving parenthesization.
- `tests/test_emitter.py` — 9 unit tests covering: `cout` vs `coutln` translation, zero-arg `cout`, generic calls, function def with indented body, empty body as `pass`, full `if/elif/else` chain, parenthesized binary ops, flat binary ops.

### Changed
- `Compiler.compile()` now runs `Lexer → Parser (rot/syntax) → Emitter`. The previous `Lexer → Parser (rot/parser, the transpiler)` flow is retired.
- `ARCHITECTURE.md` rewritten: 4-stage pipeline diagram, new Stage 2 (real parser) replacing the old "Transpiler" stage, new Stage 3 (emitter), renumbered Stage 4 (compiler).

### Removed
- `rot/parser.py` — the v1 transpiler. Replaced by the AST + emitter combination. The historical note in ARCHITECTURE.md preserves what it did.
- `tests/test_parser.py` — tested the now-dead transpiler. Behavior coverage moved to `tests/test_emitter.py` and `tests/test_end_to_end.py`.
- `PY_EQUIVALENT` dict from `rot/keywords.py` (was only consumed by the transpiler).

## [1.8.0] - 2026-05-26

Real statements. The AST can now represent every `.rot` program that runs today, including the full [examples/functions.rot](examples/functions.rot) (funct + if/elseif/else chain + top-level call).

### Added
- AST nodes: `Block`, `FuncDef`, `ElifBranch`, `IfStmt`. `Statement` union expanded to `ExprStmt | FuncDef | IfStmt`.
- Grammar rules in `rot/syntax.py`:
  - `func_def := 'funct' IDENT '(' params? ')' block`
  - `if_stmt := 'if' '(' expr ')' block (elif_branch)* else_branch?`
  - `block := '{' stmt* '}'`
- 6 new syntax tests covering simple funct defs, no-param funcs, simple `if`, full `if/elseif/else` chains, unterminated-block errors, and **the full end-to-end AST parse of `examples/functions.rot`**.

### Changed
- `_parse_statement` now dispatches: `FUNCTION` → `_parse_func_def`, `IF` → `_parse_if_stmt`, otherwise expression statement.
- The AST is still **not yet on the active compile path** — the v1 transpiler in `rot/parser.py` continues to drive `Compiler.compile()`. That moves in v1.9.0.

## [1.7.0] - 2026-05-26

Real expressions. The "`==` works by accident" quirk is dead.

### Added
- Multi-character operator tokens: `==` (`EQ_EQ`), `!=` (`NEQ`), `<=` (`LE`), `>=` (`GE`). The lexer's two-char lookahead matches them as single tokens; lone `=`, `<`, `>` still produce `SETVALUE`/`LESSTHAN`/`GREATERTHAN`.
- `ast.BinaryOp(op, left, right)` AST node; added to the `Expression` union.
- **Pratt parsing** in `rot/syntax.py`. Precedence levels: `*` `/` (5), `+` `-` (4), `<` `<=` `>` `>=` (3), `==` `!=` (2). All operators left-associative.
- Parenthesized expressions: `(1 + 2) * 3` parses with explicit grouping.
- 10 new tests across `tests/test_lexer.py` and `tests/test_syntax.py` covering multi-char ops, precedence, associativity, grouping, and binary ops nested inside call args.

### Changed
- `_SINGLE_CHAR_TOKENS` in `rot/lexer.py` no longer contains `=`, `<`, `>` — those moved to `_SOLO_FALLBACK` so the two-char check runs first.
- Transpiler is unchanged. New token kinds (`EQ_EQ`/`NEQ`/`LE`/`GE`) fall through to their lexeme via `PY_EQUIVALENT.get(kind, lexeme)`, so `==` emits as `==` to Python.

## [1.6.4] - 2026-05-26

### Changed
- README backronym swapped: `rot` now stands for **Recursive-descent Optimizing Transpiler**. Grounded in the actual recursive-descent parser shipped in v1.6.0; "optimizing" remains aspirational.

## [1.6.3] - 2026-05-26

### Added
- README tagline: `rot` now officially stands for **Reflexive Operational Transducer**. Maximum word-density per character.

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
