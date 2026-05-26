"""Hand-rolled tokenizer for .rot source.

Replaces the v1.x regex-driven pipeline. Same `Token` output, with one
upgrade: quoted string literals are now scanned as a single `STRING_LIT`
token (e.g. `"hello world"`) instead of being broken into
QUOTE / IDENT / QUOTE. This means strings can contain arbitrary content.
"""

from __future__ import annotations

from .errors import LexerError
from .keywords import KEYWORDS
from .token import Token


_SINGLE_CHAR_TOKENS: dict[str, str] = {
    "+": "ADDITION",
    "-": "SUBTRACTION",
    "*": "MULTIPLICATION",
    "/": "DIVISION",
    "%": "MODULO",
    "(": "L_PAREN",
    ")": "R_PAREN",
    "{": "L_CURLY",
    "}": "R_CURLY",
    "[": "L_BRACKET",
    "]": "R_BRACKET",
    "|": "COMMA",
    "'": "SINGLE_QUOTE",
    ".": "DOT",
    ":": "COLON",
}


# (current char, next char) -> (lexeme, kind). When the lookahead pair
# matches, both chars are consumed; otherwise we fall through to the
# single-char handler below.
_TWO_CHAR_TOKENS: dict[tuple[str, str], tuple[str, str]] = {
    ("=", "="): ("==", "EQ_EQ"),
    ("!", "="): ("!=", "NEQ"),
    ("<", "="): ("<=", "LE"),
    (">", "="): (">=", "GE"),
    ("+", "="): ("+=", "PLUS_EQ"),
    ("-", "="): ("-=", "MINUS_EQ"),
    ("*", "="): ("*=", "STAR_EQ"),
    ("/", "="): ("/=", "SLASH_EQ"),
    ("%", "="): ("%=", "PERCENT_EQ"),
}


# When the two-char check fails, these chars still produce a single-char token.
_SOLO_FALLBACK: dict[str, str] = {
    "=": "SETVALUE",
    "<": "LESSTHAN",
    ">": "GREATERTHAN",
}


def _is_identifier_start(ch: str) -> bool:
    # Identifiers start with a letter (upper or lower) or underscore.
    # Uppercase added in v2.6.0 — class names conventionally start capitalized.
    return ch == "_" or ch.isalpha()


def _is_identifier_continuation(ch: str) -> bool:
    # ...and continue with letters / underscores / digits.
    return _is_identifier_start(ch) or ch.isdigit()


class Lexer:
    def __init__(self, trace: bool = False) -> None:
        self.trace = trace
        self.source = ""
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens: list[Token] = []

    def tokenize(self, source: str) -> list[Token]:
        self.source = source
        if self.trace:
            print("-" * 30)
        while not self._at_end():
            self._scan_token()
        if self.trace:
            print("-" * 30)
        return self.tokens

    def _scan_token(self) -> None:
        start_line, start_col = self.line, self.col
        ch = self._peek()

        if ch == "/" and self._peek(1) == "/":
            self._scan_comment(start_line, start_col)
        elif ch == "\n":
            self._advance()
            self._add("\n", "NEWLINE", start_line, start_col)
        elif ch == " " or ch == "\t":
            self._scan_horizontal_space(start_line, start_col)
        elif ch.isdigit():
            self._scan_number(start_line, start_col)
        elif _is_identifier_start(ch):
            self._scan_identifier_or_keyword(start_line, start_col)
        elif ch == '"':
            self._scan_string_literal(start_line, start_col)
        elif (ch, self._peek(1)) in _TWO_CHAR_TOKENS:
            lexeme, kind = _TWO_CHAR_TOKENS[(ch, self._peek(1))]
            self._advance()
            self._advance()
            self._add(lexeme, kind, start_line, start_col)
        elif ch in _SOLO_FALLBACK:
            self._advance()
            self._add(ch, _SOLO_FALLBACK[ch], start_line, start_col)
        elif ch in _SINGLE_CHAR_TOKENS:
            self._advance()
            self._add(ch, _SINGLE_CHAR_TOKENS[ch], start_line, start_col)
        else:
            raise LexerError(f"unexpected character {ch!r}", start_line, start_col)

    def _scan_comment(self, line: int, col: int) -> None:
        start = self.pos
        while not self._at_end() and self._peek() != "\n":
            self._advance()
        self._add(self.source[start : self.pos], "COMMENT", line, col)

    def _scan_horizontal_space(self, line: int, col: int) -> None:
        start = self.pos
        while self._peek() in (" ", "\t"):
            self._advance()
        self._add(self.source[start : self.pos], "SPACE", line, col)

    def _scan_number(self, line: int, col: int) -> None:
        start = self.pos
        while self._peek().isdigit():
            self._advance()
        # Optional fractional part: only consume `.` if followed by a digit
        # (so `3.foo` lexes as NUMBER('3') + '.' + IDENT, not NUMBER('3.')).
        if self._peek() == "." and self._peek(1).isdigit():
            self._advance()  # consume `.`
            while self._peek().isdigit():
                self._advance()
        self._add(self.source[start : self.pos], "NUMBER", line, col)

    def _scan_identifier_or_keyword(self, line: int, col: int) -> None:
        start = self.pos
        while _is_identifier_continuation(self._peek()):
            self._advance()
        lexeme = self.source[start : self.pos]
        kind = KEYWORDS.get(lexeme, "IDENT")
        self._add(lexeme, kind, line, col)

    def _scan_string_literal(self, line: int, col: int) -> None:
        start = self.pos
        self._advance()  # opening "
        while not self._at_end() and self._peek() != '"':
            # Backslash escapes: consume `\` plus the next char as a unit
            # so `\"` doesn't terminate the string.
            if self._peek() == "\\":
                self._advance()  # consume backslash
                if self._at_end():
                    break
            self._advance()  # consume next char (escaped or not)
        if self._at_end():
            raise LexerError("unterminated string literal", line, col)
        self._advance()  # closing "
        self._add(self.source[start : self.pos], "STRING_LIT", line, col)

    def _at_end(self) -> bool:
        return self.pos >= len(self.source)

    def _peek(self, offset: int = 0) -> str:
        i = self.pos + offset
        return self.source[i] if i < len(self.source) else ""

    def _advance(self) -> str:
        ch = self.source[self.pos]
        self.pos += 1
        if ch == "\n":
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _add(self, lexeme: str, kind: str, line: int, col: int) -> None:
        token = Token(lexeme, kind, line, col)
        self.tokens.append(token)
        if self.trace:
            self._log(token)

    def _log(self, token: Token) -> None:
        idx = len(self.tokens) - 1
        spaces = " " * (5 - len(str(idx)))
        spaces2 = " " * (10 - len(repr(token.lexeme)))
        print(f"{idx}{spaces}|  {repr(token.lexeme)}{spaces2}|  {token.kind}")
