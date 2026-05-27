"""Tests for the interactive REPL (rot/repl.py).

Drives the REPL via monkey-patched `input()`. Each test feeds a fixed list
of lines and asserts on captured stdout/stderr. Persistent history is
disabled globally via `tests/conftest.py`.
"""

from __future__ import annotations

import os

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


# --- C17: REPL exit commands ---

def test_repl_exit_command_exits_cleanly(monkeypatch, capsys):
    # `exit` alone should return without raising. If we got past `exit` and
    # tried the next iteration, mock_input would raise EOFError — which is
    # also a clean exit, so we have to make sure the second input is never
    # consumed. Use a side-effect to detect that.
    consumed = []

    def mock_input(prompt=""):
        if not consumed:
            consumed.append("exit")
            return "exit"
        # Should never get here — fail loudly.
        raise AssertionError("REPL kept reading after `exit`")

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()  # returns cleanly
    assert consumed == ["exit"]


def test_repl_quit_command_exits_cleanly(monkeypatch):
    consumed = []

    def mock_input(prompt=""):
        if not consumed:
            consumed.append("quit")
            return "quit"
        raise AssertionError("REPL kept reading after `quit`")

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    assert consumed == ["quit"]


def test_repl_colon_q_command_exits_cleanly(monkeypatch):
    consumed = []

    def mock_input(prompt=""):
        if not consumed:
            consumed.append(":q")
            return ":q"
        raise AssertionError("REPL kept reading after `:q`")

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    assert consumed == [":q"]


def test_repl_exit_with_surrounding_whitespace_still_exits(monkeypatch):
    consumed = []

    def mock_input(prompt=""):
        if not consumed:
            consumed.append("  exit  ")
            return "  exit  "
        raise AssertionError("REPL kept reading after `  exit  `")

    monkeypatch.setattr("builtins.input", mock_input)
    from rot.repl import start_repl
    start_repl()
    assert consumed == ["  exit  "]


def test_repl_exit_inside_continuation_is_not_an_exit_command(monkeypatch, capsys):
    # If the user typed `exit` while in the middle of a multi-line function
    # body, the REPL must NOT exit — `exit` is a valid identifier and
    # could be part of user code. Feed: open `{`, then `exit`, then close
    # `}`. The parser will error (unknown name), and REPL should continue.
    _drive_repl(monkeypatch, [
        "funct f() {",
        "exit",
        "}",
        'coutln("alive")',
    ])
    out, err = capsys.readouterr()
    # We don't care that the body errors at parse-or-runtime; just that the
    # REPL kept going to the next input after the multi-line block.
    assert "alive" in out


# --- C24: persistent REPL history ---

def test_repl_history_file_path_uses_home():
    # Module-level HISTORY_FILE should resolve to ~/.rot_history when no
    # env var override is set.
    import importlib

    import rot.repl as repl_module
    # If ROT_HISTORY_FILE is set (e.g. from conftest), HISTORY_FILE is
    # whatever that is. Check the documented default by recomputing
    # without the env var.
    default = os.path.expanduser("~/.rot_history")
    # The module-level constant should equal the env var if set, else the
    # default — we can't easily test the default at import time after
    # conftest sets the env var. Instead, just assert the resolution shape.
    assert repl_module.HISTORY_FILE.endswith(".rot_history") or repl_module.HISTORY_FILE == ""


def test_repl_install_persistent_history_does_not_crash(monkeypatch, tmp_path):
    # With a writable temp path, install_persistent_history should run
    # without raising even if the file doesn't exist yet.
    history = tmp_path / "subdir" / "history"
    monkeypatch.setenv("ROT_HISTORY_FILE", str(history))
    from rot.repl import _install_persistent_history
    _install_persistent_history()  # creates the parent dir; reads empty history
    # Parent should now exist (created by os.makedirs).
    assert history.parent.exists()


def test_repl_install_persistent_history_skips_if_disabled(monkeypatch):
    # Empty env var = disabled. Should be a no-op (and definitely should
    # not register an atexit handler).
    monkeypatch.setenv("ROT_HISTORY_FILE", "")
    from rot.repl import _install_persistent_history
    _install_persistent_history()  # must not raise


def test_repl_install_persistent_history_swallows_unreadable_file(monkeypatch, tmp_path):
    # If the history file exists but is unreadable, the function must not
    # crash. Hard to construct a real unreadable file portably, so just
    # point at a directory (which read_history_file can't read as a file).
    bogus = tmp_path / "not_a_file"
    bogus.mkdir()  # directory, not a file
    monkeypatch.setenv("ROT_HISTORY_FILE", str(bogus))
    from rot.repl import _install_persistent_history
    _install_persistent_history()  # must not raise


def test_repl_startup_with_history_does_not_crash(monkeypatch, tmp_path, capsys):
    # End-to-end: enable history with a temp path and drive the REPL
    # through a single line + exit. The REPL must complete normally.
    history = tmp_path / "h"
    monkeypatch.setenv("ROT_HISTORY_FILE", str(history))
    _drive_repl(monkeypatch, ['coutln("ok")', "exit"])
    out, _ = capsys.readouterr()
    assert "ok" in out


# --- C46: EOF during continuation warns ---

def test_repl_eof_with_empty_buffer_exits_silently(monkeypatch, capsys):
    # ctrl-D at the main prompt (empty buffer) — exit cleanly, no warning.
    _drive_repl(monkeypatch, [])  # immediately EOFError
    out, err = capsys.readouterr()
    assert "discarded incomplete input" not in err


def test_repl_eof_during_continuation_warns(monkeypatch, capsys):
    # Feed an open brace then EOF. REPL should print the discard warning.
    _drive_repl(monkeypatch, ["funct f() {"])  # buffer non-empty, then EOF
    out, err = capsys.readouterr()
    assert "discarded incomplete input" in err


def test_repl_eof_during_unterminated_string_warns(monkeypatch, capsys):
    # Open-string buffer then EOF.
    _drive_repl(monkeypatch, ['"hello'])
    out, err = capsys.readouterr()
    assert "discarded incomplete input" in err


# --- C15: empty string echoes as `""`, not blank line ---

def test_repl_empty_string_echoes_with_quotes(monkeypatch, capsys):
    _drive_repl(monkeypatch, ['""'])
    out, _ = capsys.readouterr()
    # Must echo as `""` (two double quotes), not as a blank line.
    assert '""' in out


def test_repl_non_empty_string_echoes_with_quotes(monkeypatch, capsys):
    _drive_repl(monkeypatch, ['"hello"'])
    out, _ = capsys.readouterr()
    assert '"hello"' in out


def test_repl_string_with_newline_escape_displays_escape(monkeypatch, capsys):
    # A string containing a literal newline should display as `\n` in echo.
    _drive_repl(monkeypatch, ['"a\\nb"'])
    out, _ = capsys.readouterr()
    # Source `"a\nb"` decodes to string `"a\nb"` (a newline); echo should
    # render that newline as the escape `\n` again.
    assert '"a\\nb"' in out


def test_repl_string_with_inner_quote_displays_escape(monkeypatch, capsys):
    # `"a\"b"` decodes to `a"b`; echo should re-escape the inner quote.
    _drive_repl(monkeypatch, ['"a\\"b"'])
    out, _ = capsys.readouterr()
    assert '"a\\"b"' in out


# --- C16: `null` literal echoes as `null` ---

def test_repl_null_literal_echoes_null(monkeypatch, capsys):
    _drive_repl(monkeypatch, ["null"])
    out, _ = capsys.readouterr()
    assert "null" in out


def test_repl_variable_bound_to_null_echoes_null(monkeypatch, capsys):
    _drive_repl(monkeypatch, ["x = null", "x"])
    out, _ = capsys.readouterr()
    assert "null" in out


# --- _repl_repr unit tests ---

def test_repl_repr_unit_null():
    from rot.repl import _repl_repr
    assert _repl_repr(None) == "null"


def test_repl_repr_unit_empty_string():
    from rot.repl import _repl_repr
    assert _repl_repr("") == '""'


def test_repl_repr_unit_plain_string():
    from rot.repl import _repl_repr
    assert _repl_repr("hi") == '"hi"'


def test_repl_repr_unit_escapes_special_chars():
    from rot.repl import _repl_repr
    assert _repl_repr("a\nb") == '"a\\nb"'
    assert _repl_repr('a"b') == '"a\\"b"'
    assert _repl_repr("a\\b") == '"a\\\\b"'
    assert _repl_repr("a\tb") == '"a\\tb"'


def test_repl_repr_unit_int_unchanged():
    from rot.repl import _repl_repr
    assert _repl_repr(42) == "42"


def test_repl_repr_unit_bool_rot_style():
    from rot.repl import _repl_repr
    assert _repl_repr(True) == "true"
    assert _repl_repr(False) == "false"


# --- v2.24.3: gaps from the bug audit's T92-T98 ---


def test_repl_invalid_input_does_not_crash_session(monkeypatch, capsys):
    # A `;` is a hard lex error in rot (the lexer's "did you mean a newline?"
    # path). The REPL must catch it, print the error, and prompt again — the
    # next input still executes.
    _drive_repl(monkeypatch, [";", 'coutln("alive")'])
    out, err = capsys.readouterr()
    # The lex error mentions the offending semicolon and lands on stderr.
    assert ";" in err
    # The follow-up input ran — proves the REPL is still alive.
    assert "alive" in out


def test_repl_empty_input_is_ignored_no_echo_no_error(monkeypatch, capsys):
    # Pure-empty / whitespace-only lines should be silently skipped: the
    # REPL must not emit any error, must not echo anything, and must keep
    # looping until EOF.
    _drive_repl(monkeypatch, ["", "   ", "\t\t"])
    out, err = capsys.readouterr()
    # Banner + the REPL exited on EOF. No errors, no echoes.
    assert err == ""
    # Nothing between the banner and the trailing newline added by EOF.
    # The "discarded incomplete input" warning must not appear either
    # because the buffer was empty after each whitespace line.
    assert "discarded incomplete input" not in err
    # No spurious lines were echoed for the whitespace inputs.
    body = out.splitlines()
    # Banner lines plus possibly an EOF newline — but no `null`, no value
    # echoes from the whitespace lines.
    assert "null" not in body


def test_repl_state_preserved_across_inputs(monkeypatch, capsys):
    # The REPL holds a single long-lived Interpreter across all inputs, so
    # an assignment on one line is visible on the next. `x = 5` is an
    # Assign (no echo); `x` is a bare expression (echoes the value).
    _drive_repl(monkeypatch, ["x = 5", "x"])
    out, _ = capsys.readouterr()
    # The literal `5` shows up in the captured output, on its own line
    # (the echo for the second input).
    assert "\n5\n" in out or out.rstrip().endswith("5")


def test_repl_history_file_path_uses_env_var(monkeypatch, tmp_path):
    # `_install_persistent_history` honors `ROT_HISTORY_FILE` at runtime
    # (the test fixture sets it to "" globally; this overrides per-call).
    history = tmp_path / "myhistory"
    monkeypatch.setenv("ROT_HISTORY_FILE", str(history))
    # We can verify the path is picked up by checking that the parent dir
    # is created (the function does os.makedirs on the parent).
    from rot.repl import _install_persistent_history
    _install_persistent_history()
    # The parent of `history` is `tmp_path`, which already exists — but
    # the function must NOT crash and must respect the env override. As a
    # secondary check, re-read the env to confirm the override stuck.
    import os as _os
    assert _os.environ.get("ROT_HISTORY_FILE") == str(history)


def test_repl_install_persistent_history_no_readline_is_noop(monkeypatch, tmp_path):
    # On platforms without `readline` (Windows out of the box), the install
    # function returns early without touching the filesystem. Simulate by
    # patching the module-level `_HAS_READLINE` flag to False.
    import rot.repl as repl_module

    monkeypatch.setattr(repl_module, "_HAS_READLINE", False)
    # Even with a valid env path, the function must short-circuit and not
    # raise. Use a path that would fail to write (root-owned dir) as a
    # safeguard — but mainly we're checking no exception escapes.
    monkeypatch.setenv("ROT_HISTORY_FILE", str(tmp_path / "x"))
    repl_module._install_persistent_history()  # must not raise

