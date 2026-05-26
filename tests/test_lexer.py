import contextlib
import io

import pytest

from rot.errors import LexerError
from rot.lexer import Lexer


def _lex(source: str):
    with contextlib.redirect_stdout(io.StringIO()):
        return [(t.lexeme, t.kind) for t in Lexer().tokenize(source)]


def test_cout_call_tokenization():
    assert _lex('cout("hi")') == [
        ("cout", "PRINT"),
        ("(", "L_PAREN"),
        ('"', "QUOTE"),
        ("hi", "STRING"),
        ('"', "QUOTE"),
        (")", "R_PAREN"),
    ]


def test_keyword_vs_identifier_classification():
    assert _lex("cout")[0] == ("cout", "PRINT")
    assert _lex("coutln")[0] == ("coutln", "PRINTLN")
    assert _lex("funct")[0] == ("funct", "FUNCTION")
    assert _lex("if")[0] == ("if", "IF")
    assert _lex("else")[0] == ("else", "ELSE")
    assert _lex("elseif")[0] == ("elseif", "ELIF")
    assert _lex("hi")[0] == ("hi", "STRING")


def test_position_tracking_across_newlines():
    with contextlib.redirect_stdout(io.StringIO()):
        tokens = Lexer().tokenize("cout\n  hi")
    first = tokens[0]
    assert (first.line, first.col) == (1, 1)
    hi = next(t for t in tokens if t.lexeme == "hi")
    assert (hi.line, hi.col) == (2, 3)


def test_unknown_character_raises_lexer_error_with_location():
    with contextlib.redirect_stdout(io.StringIO()):
        with pytest.raises(LexerError) as exc_info:
            Lexer().tokenize("cout@")
    assert exc_info.value.line == 1
    assert exc_info.value.col == 5


def test_comment_consumes_to_end_of_line():
    tokens = _lex("// trailing comment\ncout")
    assert tokens[0] == ("// trailing comment", "COMMENT")
    assert tokens[1] == ("\n", "NEWLINE")
    assert tokens[2] == ("cout", "PRINT")


def test_closing_brace_is_a_real_token():
    # Pre-1.2.0 the lexer's catch-all `except: pass` silently dropped `}`.
    tokens = _lex("}")
    assert tokens == [("}", "R_CURLY")]
