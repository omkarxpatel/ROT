"""Tests for the recursive-descent parser (rot/syntax.py).

These exercise the AST shape end-to-end: source -> Lexer -> Parser -> AST.
"""

import pytest

from rot import ast
from rot.errors import ParserError
from rot.lexer import Lexer
from rot.syntax import Parser


def _parse(source: str) -> ast.Program:
    return Parser(Lexer().tokenize(source)).parse()


def test_println_call_with_string_literal():
    program = _parse('coutln("hello")')
    assert program == ast.Program(
        body=[
            ast.ExprStmt(
                ast.Call(
                    callee=ast.Identifier(name="coutln"),
                    args=[ast.StringLit(value="hello")],
                )
            )
        ]
    )


def test_call_with_multiple_number_args():
    program = _parse("hi(10 | 20)")
    assert program == ast.Program(
        body=[
            ast.ExprStmt(
                ast.Call(
                    callee=ast.Identifier(name="hi"),
                    args=[ast.NumberLit(value=10), ast.NumberLit(value=20)],
                )
            )
        ]
    )


def test_call_with_no_args():
    program = _parse("hi()")
    assert program == ast.Program(
        body=[ast.ExprStmt(ast.Call(callee=ast.Identifier(name="hi"), args=[]))]
    )


def test_bare_identifier_is_an_expression_statement():
    program = _parse("hi")
    assert program == ast.Program(body=[ast.ExprStmt(ast.Identifier(name="hi"))])


def test_number_literal_atom():
    program = _parse("42")
    assert program == ast.Program(body=[ast.ExprStmt(ast.NumberLit(value=42))])


def test_string_literal_strips_surrounding_quotes():
    program = _parse('"hello world"')
    assert program == ast.Program(
        body=[ast.ExprStmt(ast.StringLit(value="hello world"))]
    )


def test_unterminated_call_raises_parser_error():
    with pytest.raises(ParserError):
        _parse("coutln(")


def test_nested_call_in_args():
    program = _parse("outer(inner(1))")
    assert program == ast.Program(
        body=[
            ast.ExprStmt(
                ast.Call(
                    callee=ast.Identifier(name="outer"),
                    args=[
                        ast.Call(
                            callee=ast.Identifier(name="inner"),
                            args=[ast.NumberLit(value=1)],
                        )
                    ],
                )
            )
        ]
    )
