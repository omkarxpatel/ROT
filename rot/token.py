"""The Token dataclass — the unit of communication between lexer and parser."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Token:
    lexeme: str
    kind: str
    line: int
    col: int
