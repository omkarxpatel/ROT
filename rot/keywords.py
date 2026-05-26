"""Single source of truth for token kinds, reserved words, and their Python equivalents.

Three tables, each with one job:

- `KEYWORDS`        : reserved-word lexeme  -> token kind
- `TOKEN_PATTERNS`  : ordered list of (regex, kind) tried in order; kind=None
                     means "identifier or keyword — look up in KEYWORDS, fall
                     back to STRING".
- `PY_EQUIVALENT`   : token kind -> Python source to emit (parser falls back
                     to the raw lexeme when a kind is absent).
"""

from __future__ import annotations


KEYWORDS: dict[str, str] = {
    "cout":   "PRINT",
    "coutln": "PRINTLN",
    "funct":  "FUNCTION",
    "elseif": "ELIF",
    "if":     "IF",
    "else":   "ELSE",
}


# Order matters: longer / more specific patterns must come before the patterns
# they would otherwise overlap with (e.g. `//` before `/`).
TOKEN_PATTERNS: list[tuple[str, str | None]] = [
    (r"//[^\n]*",   "COMMENT"),
    (r"\d+",        "NUMBER"),
    (r"[a-z]+",     None),
    (r'"',          "QUOTE"),
    (r"'",          "SINGLE_QUOTE"),
    (r"\+",         "ADDITION"),
    (r"-",          "SUBTRACTION"),
    (r"\*",         "MULTIPLICATION"),
    (r"/",          "DIVISION"),
    (r"=",          "SETVALUE"),
    (r"<",          "LESSTHAN"),
    (r">",          "GREATERTHAN"),
    (r"\(",         "L_PAREN"),
    (r"\)",         "R_PAREN"),
    (r"\{",         "L_CURLY"),
    (r"\}",         "R_CURLY"),
    (r"\|",         "COMMA"),
    (r"\n",         "NEWLINE"),
    (r"[ \t]+",     "SPACE"),
]


PY_EQUIVALENT: dict[str, str] = {
    "PRINT":    "print",
    "PRINTLN":  "print*",
    "FUNCTION": "def",
    "L_CURLY":  ":",
    "R_CURLY":  "",
    "ELIF":     "elif",
    "COMMA":    ",",
}
