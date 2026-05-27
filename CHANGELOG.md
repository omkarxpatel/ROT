# Changelog

All notable changes to ROT are documented here. The project follows [Semantic Versioning](https://semver.org/).

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
