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
