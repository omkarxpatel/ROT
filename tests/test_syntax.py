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


def _expr(source: str) -> ast.Expression:
    """Parse a source snippet and return the single contained expression."""
    program = _parse(source)
    assert len(program.body) == 1
    return program.body[0].expr


def test_comparison_produces_binary_op():
    assert _expr("x > y") == ast.BinaryOp(
        op=">",
        left=ast.Identifier("x"),
        right=ast.Identifier("y"),
    )


def test_equality_uses_eq_eq_token():
    assert _expr("x == y") == ast.BinaryOp(
        op="==",
        left=ast.Identifier("x"),
        right=ast.Identifier("y"),
    )


def test_multiplication_binds_tighter_than_addition():
    # 1 + 2 * 3 should parse as 1 + (2 * 3), not (1 + 2) * 3.
    assert _expr("1 + 2 * 3") == ast.BinaryOp(
        op="+",
        left=ast.NumberLit(1),
        right=ast.BinaryOp(
            op="*",
            left=ast.NumberLit(2),
            right=ast.NumberLit(3),
        ),
    )


def test_parens_override_precedence():
    assert _expr("(1 + 2) * 3") == ast.BinaryOp(
        op="*",
        left=ast.BinaryOp(
            op="+",
            left=ast.NumberLit(1),
            right=ast.NumberLit(2),
        ),
        right=ast.NumberLit(3),
    )


def test_addition_is_left_associative():
    # 1 + 2 + 3 should be (1 + 2) + 3.
    assert _expr("1 + 2 + 3") == ast.BinaryOp(
        op="+",
        left=ast.BinaryOp(
            op="+",
            left=ast.NumberLit(1),
            right=ast.NumberLit(2),
        ),
        right=ast.NumberLit(3),
    )


def test_equality_binds_looser_than_comparison():
    # x > y == z should be (x > y) == z, since `>` has higher precedence.
    assert _expr("x > y == z") == ast.BinaryOp(
        op="==",
        left=ast.BinaryOp(
            op=">",
            left=ast.Identifier("x"),
            right=ast.Identifier("y"),
        ),
        right=ast.Identifier("z"),
    )


def test_binary_op_inside_call_args():
    program = _parse("coutln(1 + 2)")
    assert program == ast.Program(body=[
        ast.ExprStmt(
            ast.Call(
                callee=ast.Identifier("coutln"),
                args=[ast.BinaryOp(op="+", left=ast.NumberLit(1), right=ast.NumberLit(2))],
            )
        )
    ])


def test_parses_simple_function_def():
    program = _parse("funct hi(x | y) { coutln(x) }")
    assert program == ast.Program(body=[
        ast.FuncDef(
            name="hi",
            params=["x", "y"],
            body=ast.Block(statements=[
                ast.ExprStmt(
                    ast.Call(callee=ast.Identifier("coutln"), args=[ast.Identifier("x")])
                )
            ])
        )
    ])


def test_parses_function_with_no_params():
    program = _parse('funct greet() { coutln("hi") }')
    assert program == ast.Program(body=[
        ast.FuncDef(name="greet", params=[], body=ast.Block(statements=[
            ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.StringLit("hi")]))
        ]))
    ])


def test_parses_simple_if_statement():
    program = _parse("if (x > y) { coutln(x) }")
    assert program == ast.Program(body=[
        ast.IfStmt(
            cond=ast.BinaryOp(">", ast.Identifier("x"), ast.Identifier("y")),
            then_block=ast.Block(statements=[
                ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.Identifier("x")]))
            ]),
            elif_branches=[],
            else_block=None,
        )
    ])


def test_parses_if_elseif_else_chain():
    program = _parse(
        'if (x > y) { coutln(x) }\n'
        'elseif (x == y) { coutln("same") }\n'
        'else { coutln(y) }'
    )
    assert len(program.body) == 1
    stmt = program.body[0]
    assert isinstance(stmt, ast.IfStmt)
    assert stmt.cond == ast.BinaryOp(">", ast.Identifier("x"), ast.Identifier("y"))
    assert len(stmt.elif_branches) == 1
    assert stmt.elif_branches[0].cond == ast.BinaryOp("==", ast.Identifier("x"), ast.Identifier("y"))
    assert stmt.else_block is not None
    assert len(stmt.else_block.statements) == 1


def test_unterminated_block_raises_parser_error():
    with pytest.raises(ParserError):
        _parse("funct hi() { coutln(x)")


def test_full_example_functions_rot_parses_end_to_end():
    """The same program that's been our end-to-end golden since v1.0.0
    now parses to a full AST — funct + if/elseif/else chain + top-level
    call all represented as nodes."""
    import pathlib
    source = (pathlib.Path(__file__).resolve().parent.parent / "examples/functions.rot").read_text()
    program = _parse(source)

    # Two top-level statements: the funct def + the call at the end.
    assert len(program.body) == 2

    func_def = program.body[0]
    assert isinstance(func_def, ast.FuncDef)
    assert func_def.name == "hi"
    assert func_def.params == ["x", "y"]
    assert len(func_def.body.statements) == 1

    if_stmt = func_def.body.statements[0]
    assert isinstance(if_stmt, ast.IfStmt)
    assert if_stmt.cond == ast.BinaryOp(">", ast.Identifier("x"), ast.Identifier("y"))
    assert len(if_stmt.elif_branches) == 1
    assert if_stmt.else_block is not None

    call_stmt = program.body[1]
    assert isinstance(call_stmt, ast.ExprStmt)
    assert isinstance(call_stmt.expr, ast.Call)
    assert call_stmt.expr.callee == ast.Identifier("hi")
    assert call_stmt.expr.args == [ast.NumberLit(10), ast.NumberLit(10)]
