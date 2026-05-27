"""Interactive REPL for rot.

Reads a line at a time (with `...` continuation while braces are unbalanced),
parses, executes against a long-lived interpreter, and echoes the value of
bare-expression statements. Errors are printed and the loop continues — they
don't kill the session.
"""

from __future__ import annotations

import atexit
import os
import sys

try:
    import readline  # enables arrow keys + history on Unix
    _HAS_READLINE = True
except ImportError:
    readline = None  # type: ignore[assignment]
    _HAS_READLINE = False

from . import __version__, ast
from .builtins import _stringify
from .errors import RotError
from .interpreter import Interpreter
from .lexer import Lexer
from .syntax import Parser


PROMPT = "rot> "
CONT_PROMPT = "...  "

# Single-line REPL commands that exit the session cleanly. Only honored when
# the buffer is empty (otherwise the user might be typing them as part of a
# multi-line expression or string literal).
EXIT_COMMANDS = frozenset({"exit", "quit", ":q"})

# Path to the persistent REPL history file. Lines typed at the prompt are
# saved here at exit and re-loaded on the next session, so arrow-up across
# sessions surfaces previous commands. Skipped on platforms without
# `readline` (Windows out of the box). Override with the env var
# `ROT_HISTORY_FILE` (e.g. tests set this to a temp path) — set it to the
# empty string to disable history entirely.
HISTORY_FILE = os.environ.get(
    "ROT_HISTORY_FILE", os.path.expanduser("~/.rot_history")
)


def _install_persistent_history() -> None:
    """Load any existing history file and register an atexit save handler.

    Failures are silently swallowed — a broken history file or a read-only
    home directory must not prevent the REPL from starting. Skipped entirely
    if `readline` is unavailable on this platform (Windows), or if the
    `ROT_HISTORY_FILE` env var is set to an empty string."""
    if not _HAS_READLINE:
        return
    # Re-read the env var on each call so tests can toggle history at runtime.
    path = os.environ.get("ROT_HISTORY_FILE", HISTORY_FILE)
    if not path:
        return  # Empty string = disabled.
    try:
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
    except OSError:
        return  # Can't create parent — give up silently.
    try:
        readline.read_history_file(path)
    except (OSError, FileNotFoundError):
        # No history yet, or unreadable file — fine, we'll write a new one.
        pass

    def _save_history() -> None:
        try:
            readline.write_history_file(path)
        except OSError:
            pass

    atexit.register(_save_history)


def start_repl() -> None:
    _install_persistent_history()
    print(f"rot {__version__} REPL")
    print("type any expression or statement; `exit`, `quit`, `:q`, or ctrl-D to exit")
    interp = Interpreter()
    buffer: list[str] = []

    while True:
        prompt = CONT_PROMPT if buffer else PROMPT
        try:
            line = input(prompt)
        except EOFError:
            print()  # newline after ^D
            return
        except KeyboardInterrupt:
            print("\n(interrupted)")
            buffer = []
            continue

        # Exit commands — only honored when not in continuation mode, so
        # `exit` typed inside a multi-line function body or string doesn't
        # accidentally kill the REPL.
        if not buffer and line.strip() in EXIT_COMMANDS:
            return

        buffer.append(line)
        full = "\n".join(buffer)

        if _needs_more(full):
            continue

        # Reset the buffer before parsing — even if it fails we want a fresh prompt.
        buffer = []
        if not full.strip():
            continue

        try:
            tokens = Lexer().tokenize(full)
            program = Parser(tokens).parse()
        except RotError as err:
            print(f"rot error: {err}", file=sys.stderr)
            continue

        try:
            _execute_with_echo(interp, program)
        except RotError as err:
            print(f"rot error: {err}", file=sys.stderr)
        except Exception as err:
            # Catch only `Exception`, NOT `BaseException` — KeyboardInterrupt
            # and SystemExit are BaseException subclasses and must propagate
            # so the user can ctrl-C out of a runaway program. The internal
            # _ThrowSignal / _ReturnSignal / _BreakSignal / _ContinueSignal
            # types are BaseException subclasses too, but v2.15.x wrapped
            # them into RotError at every escape point, so they shouldn't
            # reach this handler anymore.
            print(f"rot error: {err}", file=sys.stderr)


def _needs_more(source: str) -> bool:
    """Heuristic: input needs continuation if `{` / `[` / `(` are unbalanced
    outside string literals, OR if a string literal is still open at the end
    of the buffer. `//`-comments are skipped (their `{`/`}` don't count).
    Doesn't handle every edge case but covers the cases the REPL hits in
    practice."""
    depth = 0
    in_string = False
    i = 0
    while i < len(source):
        ch = source[i]
        if in_string:
            # Inside a string — only `\` (escape) and unescaped `"` (close)
            # matter. Everything else is content, including braces.
            if ch == "\\" and i + 1 < len(source):
                i += 2
                continue
            if ch == '"':
                in_string = False
            i += 1
            continue
        # Outside a string.
        # `//` starts a comment that runs to the next newline. Skip the
        # comment region entirely — braces inside don't count.
        if ch == "/" and i + 1 < len(source) and source[i + 1] == "/":
            # Advance to the next newline (or end of buffer).
            while i < len(source) and source[i] != "\n":
                i += 1
            continue
        if ch == "\\" and i + 1 < len(source):
            i += 2
            continue
        if ch == '"':
            in_string = True
            i += 1
            continue
        if ch in "{[(":
            depth += 1
        elif ch in "}])":
            depth -= 1
        i += 1
    return depth > 0 or in_string


def _execute_with_echo(interp: Interpreter, program: ast.Program) -> None:
    """If the program is a single expression statement, evaluate and print
    its non-null result (Python-REPL style). Otherwise just execute."""
    if len(program.body) == 1 and isinstance(program.body[0], ast.ExprStmt):
        value = interp._evaluate(program.body[0].expr)
        if value is not None:
            print(_stringify(value))
        return
    interp.execute(program)
