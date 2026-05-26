import contextlib
import io

from rot.parser import Parser
from rot.token import Token


def _parse(*specs):
    tokens = [Token(lex, kind, 0, 0) for lex, kind in specs]
    with contextlib.redirect_stdout(io.StringIO()):
        return Parser().parse(tokens)


def test_cout_inserts_end_kwarg_for_no_newline():
    result = _parse(
        ("cout", "PRINT"),
        ("(", "L_PAREN"),
        ('"', "QUOTE"),
        ("hi", "STRING"),
        ('"', "QUOTE"),
        (")", "R_PAREN"),
    )
    assert result == 'print("hi", end="")'


def test_coutln_uses_default_print_newline():
    result = _parse(
        ("coutln", "PRINTLN"),
        ("(", "L_PAREN"),
        ('"', "QUOTE"),
        ("hi", "STRING"),
        ('"', "QUOTE"),
        (")", "R_PAREN"),
    )
    assert result == 'print("hi")'


def test_function_def_translates_to_python_def():
    result = _parse(
        ("funct", "FUNCTION"),
        (" ", "SPACE"),
        ("hi", "STRING"),
        ("(", "L_PAREN"),
        ("x", "STRING"),
        ("|", "COMMA"),
        ("y", "STRING"),
        (")", "R_PAREN"),
        (" ", "SPACE"),
        ("{", "L_CURLY"),
    )
    assert result == "def hi(x,y) :"


def test_unknown_token_kind_falls_through_to_lexeme():
    result = _parse(
        ("z", "STRING"),
        ("=", "SETVALUE"),
        ("1", "NUMBER"),
    )
    assert result == "z=1"


def test_closing_brace_emits_nothing():
    result = _parse(("}", "R_CURLY"))
    assert result == ""
