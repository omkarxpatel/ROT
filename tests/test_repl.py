"""Tests for the interactive REPL (rot/repl.py).

Drives the REPL via monkey-patched `input()`. Each test feeds a fixed list
of lines and asserts on captured stdout/stderr.
"""

from __future__ import annotations

import pytest


def _drive_repl(monkeypatch, lines):
    """Helper: feed `lines` to start_repl() via monkey-patched input()."""
    inputs = iter(lines)

    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()


# --- C11: unterminated `"` requests continuation ---

def test_repl_unterminated_string_requests_continuation(monkeypatch, capsys):
    # First line opens a string but doesn't close it. REPL should keep reading
    # until the closing quote arrives on a subsequent line.
    _drive_repl(monkeypatch, [
        'x = "hello',
        ' world"',
        'coutln(x)',
    ])
    out, _ = capsys.readouterr()
    # The captured value is "hello\n world" — multi-line string preserved.
    assert "hello" in out
    assert "world" in out


def test_repl_needs_more_returns_true_for_open_string():
    from rot.repl import _needs_more
    assert _needs_more('"hello') is True


def test_repl_needs_more_returns_false_for_closed_string():
    from rot.repl import _needs_more
    assert _needs_more('"hello"') is False


def test_repl_needs_more_handles_escaped_quote_in_string():
    from rot.repl import _needs_more
    # The \" inside the string is an escape, not a close. String still open.
    assert _needs_more('"foo \\"bar') is True


# --- C12: unterminated `f"` requests continuation ---

def test_repl_unterminated_fstring_requests_continuation(monkeypatch, capsys):
    _drive_repl(monkeypatch, [
        'name = "world"',
        'x = f"hello,',
        ' {name}"',
        'coutln(x)',
    ])
    out, _ = capsys.readouterr()
    assert "hello" in out
    assert "world" in out


def test_repl_needs_more_returns_true_for_open_fstring():
    from rot.repl import _needs_more
    assert _needs_more('f"hi {x}') is True


# --- Don't count braces inside a string ---

def test_repl_needs_more_ignores_braces_inside_string():
    from rot.repl import _needs_more
    # `{` is inside the string — should not request continuation.
    assert _needs_more('"foo { bar"') is False


def test_repl_needs_more_ignores_closing_brace_inside_string():
    from rot.repl import _needs_more
    assert _needs_more('"foo } bar"') is False


# --- C13: `//` comments don't confuse the brace counter ---

def test_repl_needs_more_ignores_open_brace_in_comment():
    from rot.repl import _needs_more
    # `{` is inside a `//` comment — should not request continuation.
    assert _needs_more("// {") is False


def test_repl_needs_more_ignores_close_brace_in_comment():
    from rot.repl import _needs_more
    assert _needs_more("// }") is False


def test_repl_needs_more_only_skips_to_end_of_line_in_comment():
    from rot.repl import _needs_more
    # The `{` on line 1 is in a comment. The `{` on line 2 is real.
    assert _needs_more("// {\n{") is True


def test_repl_needs_more_handles_comment_after_real_brace():
    from rot.repl import _needs_more
    # Real `{` opens a block; `// }` is a comment, doesn't close anything.
    assert _needs_more("{ // }") is True


def test_repl_comment_with_brace_does_not_hang(monkeypatch, capsys):
    # Regression for C13: a `{` inside a `//` comment used to put the REPL
    # into perma-continuation. Single-line `// {` should execute and the REPL
    # should be ready for the next input.
    _drive_repl(monkeypatch, [
        "// {",
        'coutln("alive")',
    ])
    out, _ = capsys.readouterr()
    assert "alive" in out


# --- C14: KeyboardInterrupt must propagate, not be swallowed ---

def test_repl_keyboard_interrupt_during_execute_propagates(monkeypatch):
    # If user code (or a builtin) raises KeyboardInterrupt while executing,
    # the REPL's exception handler must NOT swallow it — otherwise the user
    # can never ctrl-C out of a runaway loop. Simulate by patching
    # `_execute_with_echo` to raise KeyboardInterrupt on the first call.
    raised = {"done": False}

    def fake_execute(interp, program):
        if not raised["done"]:
            raised["done"] = True
            raise KeyboardInterrupt

    monkeypatch.setattr("rot.repl._execute_with_echo", fake_execute)

    # input() returns once with a benign expression; on the second call
    # (after the KeyboardInterrupt would have killed the REPL) it'd raise
    # EOFError, but we should never get there.
    inputs = iter(["1 + 1"])

    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    with pytest.raises(KeyboardInterrupt):
        start_repl()


def test_repl_system_exit_during_execute_propagates(monkeypatch):
    # SystemExit is also BaseException; should not be swallowed either.
    def fake_execute(interp, program):
        raise SystemExit(0)

    monkeypatch.setattr("rot.repl._execute_with_echo", fake_execute)

    inputs = iter(["1 + 1"])

    def mock_input(prompt=""):
        try:
            return next(inputs)
        except StopIteration:
            raise EOFError

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    with pytest.raises(SystemExit):
        start_repl()
