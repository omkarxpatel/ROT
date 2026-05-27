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


def test_uppercase_identifiers_supported_for_class_names():
    # Class names conventionally start capitalized (Point, Counter, etc.).
    # Identifier rule since v2.6.0: [A-Za-z_][A-Za-z_0-9]*
    assert _lex("Point") == [("Point", "IDENT")]
    assert _lex("x1") == [("x1", "IDENT")]
    assert _lex("MyClass") == [("MyClass", "IDENT")]


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


def test_return_is_a_keyword():
    assert _lex("return")[0] == ("return", "RETURN")
    # Identifier that contains "return" as a prefix is still IDENT, not RETURN.
    assert _lex("returns")[0] == ("returns", "IDENT")


def test_identifiers_can_contain_underscores():
    assert _lex("hello_world") == [("hello_world", "IDENT")]
    assert _lex("_private") == [("_private", "IDENT")]
    assert _lex("_") == [("_", "IDENT")]


def test_new_keywords_are_classified():
    assert _lex("while")[0] == ("while", "WHILE")
    assert _lex("true")[0] == ("true", "TRUE")
    assert _lex("false")[0] == ("false", "FALSE")
    assert _lex("null")[0] == ("null", "NULL")
    assert _lex("and")[0] == ("and", "AND")
    assert _lex("or")[0] == ("or", "OR")
    assert _lex("not")[0] == ("not", "NOT")


def test_modulo_is_a_single_char_token():
    assert _lex("a % b") == [
        ("a", "IDENT"), (" ", "SPACE"),
        ("%", "MODULO"),
        (" ", "SPACE"), ("b", "IDENT"),
    ]


def test_float_literals():
    tokens = _lex("3.14")
    assert tokens == [("3.14", "NUMBER")]

    # `3.foo` should be NUMBER('3'), then `.` then IDENT — but `.` isn't
    # lexable yet, so this is just verifying the boundary behavior:
    tokens = _lex("42")
    assert tokens == [("42", "NUMBER")]


def test_string_literal_with_escapes():
    tokens = _lex(r'"hello\nworld"')
    assert tokens == [(r'"hello\nworld"', "STRING_LIT")]

    # Escaped quote inside a string should not terminate it.
    tokens = _lex(r'"he said \"hi\""')
    assert tokens == [(r'"he said \"hi\""', "STRING_LIT")]


def test_compound_assign_tokens():
    assert _lex("x += 1") == [
        ("x", "IDENT"), (" ", "SPACE"),
        ("+=", "PLUS_EQ"),
        (" ", "SPACE"), ("1", "NUMBER"),
    ]
    assert _lex("-=")[0] == ("-=", "MINUS_EQ")
    assert _lex("*=")[0] == ("*=", "STAR_EQ")
    assert _lex("/=")[0] == ("/=", "SLASH_EQ")
    assert _lex("%=")[0] == ("%=", "PERCENT_EQ")


# v2.20.1 — L1: tokenize() must reset state between calls.
def test_lexer_reuse_returns_correct_tokens_on_second_call():
    lex = Lexer()
    first = lex.tokenize("abc")
    second = lex.tokenize("xyz")
    assert [(t.lexeme, t.kind) for t in first] == [("abc", "IDENT")]
    assert [(t.lexeme, t.kind) for t in second] == [("xyz", "IDENT")]


def test_lexer_reuse_resets_position_tracking():
    lex = Lexer()
    lex.tokenize("a\nb\nc")
    # Second call to a single-line source should track line 1, not pick up
    # the previous call's incremented line counter.
    tokens = lex.tokenize("hi")
    assert tokens[0].line == 1
    assert tokens[0].col == 1


# v2.20.1 — L60: tokenize() returns a fresh list, not a shared reference.
def test_tokenize_returns_fresh_list_not_internal_reference():
    lex = Lexer()
    result = lex.tokenize("abc")
    result.clear()
    # The lexer's internal tokens list should be untouched by caller mutation.
    assert len(lex.tokens) == 1
    assert lex.tokens[0].lexeme == "abc"


# v2.20.2 — L2: bare CR (old-Mac line ending) must advance line.
def test_bare_cr_advances_line():
    tokens = Lexer().tokenize("a\rb\rc")
    a = next(t for t in tokens if t.lexeme == "a")
    b = next(t for t in tokens if t.lexeme == "b")
    c = next(t for t in tokens if t.lexeme == "c")
    assert (a.line, a.col) == (1, 1)
    assert (b.line, b.col) == (2, 1)
    assert (c.line, c.col) == (3, 1)


def test_crlf_advances_line_once():
    tokens = Lexer().tokenize("a\r\nb")
    a = next(t for t in tokens if t.lexeme == "a")
    b = next(t for t in tokens if t.lexeme == "b")
    assert (a.line, a.col) == (1, 1)
    assert (b.line, b.col) == (2, 1)


# v2.20.2 — L4: comment with bare CR must stop at the CR, not consume to EOF.
def test_comment_with_bare_cr_stops_at_cr():
    tokens = Lexer().tokenize("// foo\r bar")
    # First token: a comment that stops at the CR (no `bar` swallowed).
    assert tokens[0].lexeme == "// foo"
    assert tokens[0].kind == "COMMENT"
    # Verify the source after the CR continues to be tokenized: we expect a
    # NEWLINE, then a SPACE, then the IDENT `bar`.
    later = [(t.lexeme, t.kind) for t in tokens[1:]]
    assert ("bar", "IDENT") in later


# v2.20.3 — L3: trailing \r must not be captured in COMMENT lexeme on CRLF.
def test_crlf_comment_does_not_capture_trailing_cr():
    tokens = Lexer().tokenize("// foo\r\nbar")
    comment = tokens[0]
    assert comment.kind == "COMMENT"
    # Comment lexeme stops before the \r (and certainly before the \n).
    assert comment.lexeme == "// foo"
    assert "\r" not in comment.lexeme


# v2.20.4 — L5: an unclosed `{` in an f-string must error at lex time.
def test_fstring_unclosed_interpolation_brace_errors_at_lex_time():
    with pytest.raises(LexerError) as exc_info:
        Lexer().tokenize('f"hi {x"')
    assert "unclosed '{' in f-string" in str(exc_info.value)


def test_fstring_unclosed_brace_followed_by_eof_errors():
    with pytest.raises(LexerError) as exc_info:
        Lexer().tokenize('f"abc {')
    # Either "unclosed '{' in f-string" or "unterminated f-string" is fine,
    # but the brace-imbalance message is the more informative one.
    assert "unclosed '{' in f-string" in str(exc_info.value)


def test_fstring_well_formed_interpolation_still_works():
    # Regression: balanced braces must not trip the new check.
    tokens = Lexer().tokenize('f"hi {name}, you are {age}"')
    assert len(tokens) == 1
    assert tokens[0].kind == "FSTRING"
