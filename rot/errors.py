"""Exception types raised by the lexer and parser.

All errors carry a (line, col) source location so the CLI can present them
in a single consistent format.
"""

from __future__ import annotations


class RotError(Exception):
    def __init__(self, message: str, line: int = 0, col: int = 0) -> None:
        prefix = f"line {line}:{col}: " if line else ""
        super().__init__(f"{prefix}{message}")
        self.line = line
        self.col = col


class LexerError(RotError):
    pass


class ParserError(RotError):
    pass
