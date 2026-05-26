import pytest

from rot.errors import LexerError
from rot.lexer import Lexer


def _lex(source: str):
    return [(t.lexeme, t.kind) for t in Lexer().tokenize(source)]


def test_cout_call_tokenization():
    assert _lex('cout("hi")') == [
        ("cout", "PRINT"),
        ("(", "L_PAREN"),
        ('"hi"', "STRING_LIT"),
        (")", "R_PAREN"),
    ]


def test_string_literal_can_contain_spaces_and_punctuation():
    tokens = _lex('coutln("hello, world!")')
    assert tokens == [
        ("coutln", "PRINTLN"),
        ("(", "L_PAREN"),
        ('"hello, world!"', "STRING_LIT"),
        (")", "R_PAREN"),
    ]


def test_unterminated_string_literal_raises():
    with pytest.raises(LexerError) as exc_info:
        Lexer().tokenize('coutln("oops')
    assert exc_info.value.line == 1
    assert exc_info.value.col == 8


def test_keyword_vs_identifier_classification():
    assert _lex("cout")[0] == ("cout", "PRINT")
    assert _lex("coutln")[0] == ("coutln", "PRINTLN")
    assert _lex("funct")[0] == ("funct", "FUNCTION")
    assert _lex("if")[0] == ("if", "IF")
    assert _lex("else")[0] == ("else", "ELSE")
    assert _lex("elseif")[0] == ("elseif", "ELIF")
    assert _lex("hi")[0] == ("hi", "IDENT")


def test_position_tracking_across_newlines():
    tokens = Lexer().tokenize("cout\n  hi")
    first = tokens[0]
    assert (first.line, first.col) == (1, 1)
    hi = next(t for t in tokens if t.lexeme == "hi")
    assert (hi.line, hi.col) == (2, 3)


def test_unknown_character_raises_lexer_error_with_location():
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
    tokens = _lex("}")
    assert tokens == [("}", "R_CURLY")]


def test_uppercase_identifiers_are_unsupported():
    # rot keywords and identifiers are lowercase by design.
    with pytest.raises(LexerError):
        Lexer().tokenize("HELLO")


def test_multi_char_operators_are_single_tokens():
    assert _lex("x == y") == [
        ("x", "IDENT"), (" ", "SPACE"),
        ("==", "EQ_EQ"),
        (" ", "SPACE"), ("y", "IDENT"),
    ]
    assert _lex("x != y") == [
        ("x", "IDENT"), (" ", "SPACE"),
        ("!=", "NEQ"),
        (" ", "SPACE"), ("y", "IDENT"),
    ]
    assert _lex("x <= y") == [
        ("x", "IDENT"), (" ", "SPACE"),
        ("<=", "LE"),
        (" ", "SPACE"), ("y", "IDENT"),
    ]
    assert _lex("x >= y") == [
        ("x", "IDENT"), (" ", "SPACE"),
        (">=", "GE"),
        (" ", "SPACE"), ("y", "IDENT"),
    ]


def test_solo_equals_still_setvalue():
    # A lone `=` (not followed by another `=`) still produces SETVALUE.
    assert _lex("x = y") == [
        ("x", "IDENT"), (" ", "SPACE"),
        ("=", "SETVALUE"),
        (" ", "SPACE"), ("y", "IDENT"),
    ]


def test_bare_exclamation_is_unsupported():
    # `!` is only valid as part of `!=`.
    with pytest.raises(LexerError):
        Lexer().tokenize("!x")
