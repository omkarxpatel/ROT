"""Keyword and Python-equivalent lookups.

Two tables:

- `KEYWORDS`       : reserved-word lexeme -> token kind. The lexer
                     consults this after scanning a lowercase
                     identifier to decide if it's a real keyword.
- `PY_EQUIVALENT`  : token kind -> Python source emitted by the
                     transpiler (falls back to the raw lexeme when a
                     kind is absent).
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


PY_EQUIVALENT: dict[str, str] = {
    "PRINT":    "print",
    "PRINTLN":  "print*",
    "FUNCTION": "def",
    "L_CURLY":  ":",
    "R_CURLY":  "",
    "ELIF":     "elif",
    "COMMA":    ",",
}
