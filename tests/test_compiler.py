"""Tests for the orchestrator (rot/compiler.py).

Drives `Compiler` directly (no subprocess) so each test is fast and can
inspect captured stdout/stderr precisely. Covers:

- `parse(source)` → `ast.Program` shape
- `run(source, source_path=...)` setting the interpreter's source_dir
  so relative imports resolve against that file's directory
- `trace=True` printing the per-stage tokenizer / parser / interpreter
  trace to stdout
- Reusing the same `Compiler` across multiple `run()` calls — each call
  spins up a fresh `Interpreter`, so user bindings don't leak between
  runs and the frozen-builtins layer (v2.16.5) keeps its semantics
- `RecursionError` during parse converting to `ParserError` (v2.14.10)
"""

from __future__ import annotations

import contextlib
import io
import pathlib

import pytest

from rot import ast
from rot.compiler import Compiler
from rot.errors import InterpreterError, ParserError


# --- parse returns a Program ---

def test_compiler_parse_returns_program_ast():
    prog = Compiler().parse('coutln("hi")\n')
    assert isinstance(prog, ast.Program)
    # A single coutln statement produces one ExprStmt at the top level.
    assert len(prog.body) == 1


def test_compiler_parse_empty_source_returns_empty_program():
    prog = Compiler().parse("")
    assert isinstance(prog, ast.Program)
    assert prog.body == []


# --- trace=True prints per-stage headers ---

def test_compiler_trace_prints_tokenizer_parser_interpreter_headers(capsys):
    Compiler(trace=True).run('coutln("ok")\n')
    out, _ = capsys.readouterr()
    # The trace prints three sectioned headers in order.
    assert "Process 1 - Tokenizer" in out
    assert "Process 2 - Parser" in out
    assert "Process 3 - Interpreter" in out
    # And the token rows for the actual tokens (PRINTLN keyword for `coutln`).
    assert "PRINTLN" in out
    # The interpreted output is still emitted under trace mode.
    assert "ok" in out


def test_compiler_trace_off_does_not_print_stage_headers(capsys):
    # trace=False (the default) must not emit "Process 1" / "Tokenizer" /
    # "Parser" headers. Only the program's own output should appear.
    Compiler(trace=False).run('coutln("only")\n')
    out, _ = capsys.readouterr()
    assert "Process 1" not in out
    assert "Tokenizer" not in out
    assert out.strip() == "only"


# --- source_path → source_dir ---

def test_compiler_run_with_source_path_resolves_relative_imports(tmp_path: pathlib.Path):
    # Build a two-file project in tmp_path. main.rot imports lib.rot via a
    # bare name; the import resolves relative to main.rot's directory only
    # because the compiler passes its dir to the interpreter.
    (tmp_path / "lib.rot").write_text('x = 99\n')
    main = tmp_path / "main.rot"
    main.write_text('import "lib"\ncoutln(x)\n')

    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Compiler().run(main.read_text(), source_path=str(main))

    assert buf.getvalue().strip() == "99"


def test_compiler_run_without_source_path_uses_cwd_for_imports(tmp_path: pathlib.Path, monkeypatch):
    # Without source_path, the interpreter falls back to os.getcwd() for
    # resolving relative imports.
    (tmp_path / "lib.rot").write_text('y = 7\n')
    monkeypatch.chdir(tmp_path)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        Compiler().run('import "lib"\ncoutln(y)\n')
    assert buf.getvalue().strip() == "7"


# --- Compiler reuse across runs ---

def test_compiler_reused_across_runs_does_not_leak_user_bindings(capsys):
    # Each `run` creates a fresh Interpreter (no state shared), so a binding
    # in the first run is gone in the second.
    c = Compiler()
    c.run("x = 5\ncoutln(x)\n")
    # Second run: referencing `x` must error because the prior interpreter's
    # globals went out of scope when its run() returned.
    with pytest.raises(InterpreterError, match="name 'x' is not defined"):
        c.run("coutln(x)\n")
    out, _ = capsys.readouterr()
    # The first run still printed `5` before we ran the second.
    assert "5" in out


def test_compiler_reused_across_runs_preserves_frozen_builtins(capsys):
    # v2.16.5: builtins live in a frozen env at the root of every fresh
    # Interpreter. Reusing a Compiler must continue to reject builtin
    # reassignment on every run.
    c = Compiler()
    with pytest.raises(InterpreterError, match="cannot reassign builtin"):
        c.run("pi = 3.0\n")
    with pytest.raises(InterpreterError, match="cannot reassign builtin"):
        c.run("cout = \"x\"\n")


# --- RecursionError during parse → ParserError (v2.14.10) ---

def test_compiler_parse_recursion_error_becomes_parser_error():
    # Pathologically deep parenthesization exceeds the Python recursion
    # limit during recursive-descent. The compiler wraps the Python
    # RecursionError as a clean ParserError so it surfaces uniformly.
    nested = "(" * 5000 + "x" + ")" * 5000
    with pytest.raises(ParserError, match="too deeply nested"):
        Compiler().parse(nested)
