"""Tokenizer: turns .rot source text into a list of `Token`s with line/col info."""

from __future__ import annotations

import re

from .errors import LexerError
from .keywords import KEYWORDS, TOKEN_PATTERNS
from .token import Token


_COMPILED_PATTERNS: list[tuple[re.Pattern[str], str | None]] = [
    (re.compile(pattern), kind) for pattern, kind in TOKEN_PATTERNS
]


class Lexer:
    def __init__(self, trace: bool = False) -> None:
        self.trace = trace
        self.position = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    def tokenize(self, source: str) -> list[Token]:
        if self.trace:
            print("-" * 30)
        while self.position < len(source):
            if not self._consume_one(source):
                raise LexerError(
                    f"unexpected character {source[self.position]!r}",
                    self.line,
                    self.col,
                )
        if self.trace:
            print("-" * 30)
        return self.tokens

    def _consume_one(self, source: str) -> bool:
        for pattern, kind in _COMPILED_PATTERNS:
            match = pattern.match(source, self.position)
            if not match or match.end() == self.position:
                continue

            lexeme = match.group(0)
            resolved_kind = kind if kind is not None else KEYWORDS.get(lexeme, "STRING")

            token = Token(lexeme, resolved_kind, self.line, self.col)
            self.tokens.append(token)
            self._log(token)
            self._advance(lexeme)
            self.position = match.end()
            return True
        return False

    def _advance(self, lexeme: str) -> None:
        newlines = lexeme.count("\n")
        if newlines:
            self.line += newlines
            self.col = len(lexeme) - lexeme.rfind("\n")
        else:
            self.col += len(lexeme)

    def _log(self, token: Token) -> None:
        if not self.trace:
            return
        idx = len(self.tokens) - 1
        spaces = " " * (5 - len(str(idx)))
        spaces2 = " " * (10 - len(repr(token.lexeme)))
        print(f"{idx}{spaces}|  {repr(token.lexeme)}{spaces2}|  {token.kind}")
