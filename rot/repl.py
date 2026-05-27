"""Interactive REPL for rot.

Reads a line at a time (with `...` continuation while braces are unbalanced),
parses, executes against a long-lived interpreter, and echoes the value of
bare-expression statements. Errors are printed and the loop continues — they
don't kill the session.
"""

from __future__ import annotations

import sys

try:
    import readline  # noqa: F401 — enables arrow keys + history on Unix
except ImportError:
    pass

from . import __version__, ast
from .builtins import _stringify
from .errors import RotError
from .interpreter import Interpreter
from .lexer import Lexer
from .syntax import Parser


PROMPT = "rot> "
CONT_PROMPT = "...  "


def start_repl() -> None:
    print(f"rot {__version__} REPL")
    print("type any expression or statement; ctrl-D to exit")
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
        except BaseException as err:
            # _ThrowSignal / _ReturnSignal can escape if used at top level.
            print(f"rot error: {err}", file=sys.stderr)


def _needs_more(source: str) -> bool:
    """Heuristic: input needs continuation if `{` / `[` / `(` are unbalanced
    outside string literals, OR if a string literal is still open at the end
    of the buffer. Doesn't handle every edge case but covers the cases the
    REPL hits in practice."""
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
