"""Reserved-word lookup consulted by the lexer.

Only one table left: KEYWORDS. The lexer scans a run of identifier
characters and looks the lexeme up here, tagging the token as the kind
returned (or ``IDENT`` if not present). The identifier rule has been
``[A-Za-z_][A-Za-z_0-9]*`` since v2.6.0 — uppercase was admitted when
class names landed; the docstring previously claimed "lowercase
letters" only, which is no longer accurate. All current keywords are
themselves lowercase, so a mixed-case lexeme like ``If`` is correctly
classified as ``IDENT`` (since v2.6.0).

Comments in rot use ``//`` (C-style), not ``#``.

PY_EQUIVALENT was retired in v1.9.0 along with the token-to-string
transpiler. The standalone emitter that briefly owned the
token-kind-to-Python translation was removed in v2.23.0.
"""

from __future__ import annotations


KEYWORDS: dict[str, str] = {
    "cout":   "PRINT",
    "coutln": "PRINTLN",
    "funct":  "FUNCTION",
    "elseif": "ELIF",
    "if":     "IF",
    "else":   "ELSE",
    "return": "RETURN",
    "while":  "WHILE",
    "true":   "TRUE",
    "false":  "FALSE",
    "null":   "NULL",
    "and":    "AND",
    "or":     "OR",
    "not":    "NOT",
    "for":      "FOR",
    "in":       "IN",
    "break":    "BREAK",
    "continue": "CONTINUE",
    "class":    "CLASS",
    "this":     "THIS",
    "try":      "TRY",
    "catch":    "CATCH",
    "throw":    "THROW",
    "import":   "IMPORT",
    "let":      "LET",
}
