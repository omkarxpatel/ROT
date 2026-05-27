"""Exception types raised by the lexer, parser, and interpreter.

All errors carry a (line, col) source location so the CLI can present them
in a single consistent format. Errors also know how to render themselves
in a rustc-style block:

    error: <message>
     --> file.rot:5:7
      |
    5 |     cout(x + +)
      |              ^

The simple ``str(err)`` shape (``"line N:C: msg"``) is preserved for
test-suite compatibility; the rustc-style block is opt-in via
``RotError.format(source, filename)`` and is what the CLI / REPL now
print.
"""

from __future__ import annotations


class RotError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0) -> None:
        prefix = f"line {line}:{col}: " if line else ""
        # Store the bare message — without the prefix — so ``format``
        # can re-render cleanly without the prefix getting embedded
        # inside the rustc-style block.
        self.message = message
        super().__init__(f"{prefix}{message}")
        self.line = line
        self.col = col

    def format(self, source: str = "", filename: str = "<source>") -> str:
        """Render this error in a rustc-style block.

        When ``line == 0`` (no location), falls back to the bare
        ``f"error: {message}"`` form — no source line, no caret. When
        ``source`` is empty (no source string available, e.g. an early
        error before any source was read), the source-line + caret block
        is also skipped.

        Format:

            error: <message>
             --> file.rot:5:7
              |
            5 |     cout(x + +)
              |              ^

        The line gutter pads to the width of the line-number digits so
        the body and caret align even for files with thousands of lines.
        """
        # No location → bare error line only.
        if not self.line:
            return f"error: {self.message}"
        header = f"error: {self.message}\n --> {filename}:{self.line}:{self.col}"
        if not source:
            # We have a location but no source string — emit just the
            # header. Better than nothing.
            return header
        lines = source.splitlines()
        if self.line <= 0 or self.line > len(lines):
            # Out-of-bounds line — emit just the header. Shouldn't
            # normally happen, but defensive.
            return header
        src_line = lines[self.line - 1]
        # Right-align the line number to match the empty-gutter rows.
        gutter_w = len(str(self.line))
        empty_gutter = " " * gutter_w
        # Build the lines: header / blank gutter row / numbered source /
        # blank gutter row + caret.
        out: list[str] = [
            header,
            f"{empty_gutter} |",
            f"{self.line:>{gutter_w}} | {src_line}",
            # Caret line. Column is 1-indexed; the gutter prefix is
            # `<gutter_w spaces> | ` — three extra chars (` | `) plus
            # `col - 1` to land under the source character.
            f"{empty_gutter} | {' ' * (self.col - 1)}^",
        ]
        return "\n".join(out)


class LexerError(RotError):
    pass


class ParserError(RotError):
    pass


class InterpreterError(RotError):
    pass
