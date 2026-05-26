"""Parser: turns a token stream into a Python source string."""

from __future__ import annotations

from .errors import ParserError
from .keywords import PY_EQUIVALENT
from .token import Token


class Parser:
    def __init__(self, trace: bool = False) -> None:
        self.trace = trace

    def parse(self, tokens: list[Token]) -> str:
        if self.trace:
            print("-" * 30)
        result = ""

        for i, token in enumerate(tokens):
            parsed = self._python_for(token)

            if parsed == "print":
                self._insert_end_kwarg(tokens, i + 1, token)
            elif parsed == "print*":
                parsed = parsed.rstrip("*")

            if parsed == "print" and result[-5:] == "print":
                self._log(i, token.lexeme, parsed, token.kind)
                continue

            result += parsed
            self._log(i, token.lexeme, parsed, token.kind)

        if self.trace:
            print("-" * 30)
        return result

    @staticmethod
    def _python_for(token: Token) -> str:
        if token.kind == "COMMENT":
            return "# " + token.lexeme[2:]
        return PY_EQUIVALENT.get(token.kind, token.lexeme)

    @staticmethod
    def _insert_end_kwarg(tokens: list[Token], start: int, origin: Token) -> None:
        open_parens = 0
        for i in range(start, len(tokens)):
            if tokens[i].kind == "L_PAREN":
                open_parens += 1
            elif tokens[i].kind == "R_PAREN":
                open_parens -= 1
                if open_parens == 0:
                    end = Token(', end=""', "ENDL", tokens[i].line, tokens[i].col)
                    tokens.insert(i, end)
                    return
        raise ParserError(
            "unterminated cout(...) — no matching ')' found",
            origin.line,
            origin.col,
        )

    def _log(self, idx: int, raw: str, parsed: str, kind: str) -> None:
        if not self.trace:
            return
        if parsed == "\n" or kind == "SPACE":
            raw, parsed = repr(raw), repr(parsed)
        spaces = " " * (5 - len(str(idx + 1)))
        spaces2 = " " * (10 - len(str(raw)))
        print(f"{idx + 1}{spaces}|  {raw}{spaces2}->    {parsed}")
