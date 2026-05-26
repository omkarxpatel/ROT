"""Reserved-word lookup consulted by the lexer.

Only one table left: KEYWORDS. The lexer scans a run of lowercase
letters, looks the lexeme up here, and tags the token as the kind
returned (or `IDENT` if not present).

PY_EQUIVALENT was retired in v1.9.0 along with the token-to-string
transpiler. The AST emitter (rot/emitter.py) now owns the
token-kind-to-Python translation.
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
}
