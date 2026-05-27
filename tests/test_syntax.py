"""Tests for the recursive-descent parser (rot/syntax.py).

These exercise the AST shape end-to-end: source -> Lexer -> Parser -> AST.
"""

import dataclasses

import pytest

from rot import ast
from rot.errors import ParserError
from rot.lexer import Lexer
from rot.syntax import Parser


def _parse(source: str) -> ast.Program:
    return Parser(Lexer().tokenize(source)).parse()


def _strip_pos(node):
    """v2.22.2: the parser now stamps every AST node with `line` / `col`.
    Most equality-based tests below predate that change and compare nodes
    against literals constructed without positions. Walk the tree zeroing
    `line` and `col` so the literal-style comparison continues to verify
    the AST SHAPE without coupling tests to source positions. Tests that
    care about positions can compare on raw nodes."""
    if dataclasses.is_dataclass(node):
        for f in dataclasses.fields(node):
            v = getattr(node, f.name)
            if f.name in ("line", "col"):
                setattr(node, f.name, 0)
            else:
                _strip_pos(v)
        return node
    if isinstance(node, list):
        for item in node:
            _strip_pos(item)
        return node
    if isinstance(node, tuple):
        for item in node:
            _strip_pos(item)
        return node
    return node


def test_println_call_with_string_literal():
    program = _strip_pos(_parse('coutln("hello")'))
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
    program = _strip_pos(_parse("hi(10 | 20)"))
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
    program = _strip_pos(_parse("hi()"))
    assert program == ast.Program(
        body=[ast.ExprStmt(ast.Call(callee=ast.Identifier(name="hi"), args=[]))]
    )


def test_bare_identifier_is_an_expression_statement():
    program = _strip_pos(_parse("hi"))
    assert program == ast.Program(body=[ast.ExprStmt(ast.Identifier(name="hi"))])


def test_number_literal_atom():
    program = _strip_pos(_parse("42"))
    assert program == ast.Program(body=[ast.ExprStmt(ast.NumberLit(value=42))])


def test_string_literal_strips_surrounding_quotes():
    program = _strip_pos(_parse('"hello world"'))
    assert program == ast.Program(
        body=[ast.ExprStmt(ast.StringLit(value="hello world"))]
    )


def test_unterminated_call_raises_parser_error():
    with pytest.raises(ParserError):
        _parse("coutln(")


def test_nested_call_in_args():
    program = _strip_pos(_parse("outer(inner(1))"))
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
    """Parse a source snippet and return the single contained expression.
    Source positions are stripped so the returned AST compares cleanly
    against position-less literal constructions."""
    program = _strip_pos(_parse(source))
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
    program = _strip_pos(_parse("coutln(1 + 2)"))
    assert program == ast.Program(body=[
        ast.ExprStmt(
            ast.Call(
                callee=ast.Identifier("coutln"),
                args=[ast.BinaryOp(op="+", left=ast.NumberLit(1), right=ast.NumberLit(2))],
            )
        )
    ])


def test_parses_simple_function_def():
    program = _strip_pos(_parse("funct hi(x | y) { coutln(x) }"))
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
    program = _strip_pos(_parse('funct greet() { coutln("hi") }'))
    assert program == ast.Program(body=[
        ast.FuncDef(name="greet", params=[], body=ast.Block(statements=[
            ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.StringLit("hi")]))
        ]))
    ])


def test_parses_simple_if_statement():
    program = _strip_pos(_parse("if (x > y) { coutln(x) }"))
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
    program = _strip_pos(_parse(
        'if (x > y) { coutln(x) }\n'
        'elseif (x == y) { coutln("same") }\n'
        'else { coutln(y) }'
    ))
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


def test_assignment_produces_assign_node():
    program = _strip_pos(_parse("x = 5"))
    assert program == ast.Program(body=[
        ast.Assign(name="x", value=ast.NumberLit(5))
    ])


def test_assignment_distinguished_from_equality_expr():
    # x == y is an expression statement; x = y is an assignment.
    eq = _parse("x == y")
    assert isinstance(eq.body[0], ast.ExprStmt)
    assert isinstance(eq.body[0].expr, ast.BinaryOp)

    asg = _parse("x = y")
    assert isinstance(asg.body[0], ast.Assign)


def test_assignment_value_can_be_a_complex_expression():
    program = _strip_pos(_parse("total = a + b * 2"))
    assert program.body[0] == ast.Assign(
        name="total",
        value=ast.BinaryOp(
            op="+",
            left=ast.Identifier("a"),
            right=ast.BinaryOp(op="*", left=ast.Identifier("b"), right=ast.NumberLit(2)),
        ),
    )


def test_return_with_expression():
    program = _strip_pos(_parse("funct add(x | y) { return x + y }"))
    func = program.body[0]
    assert isinstance(func, ast.FuncDef)
    ret = func.body.statements[0]
    assert isinstance(ret, ast.Return)
    assert ret.value == ast.BinaryOp(op="+", left=ast.Identifier("x"), right=ast.Identifier("y"))


def test_bare_return_has_no_value():
    program = _parse("funct foo() { return }")
    ret = program.body[0].body.statements[0]
    assert isinstance(ret, ast.Return)
    assert ret.value is None


def test_parses_while_statement():
    program = _strip_pos(_parse("while (i < 10) { i = i + 1 }"))
    assert program == ast.Program(body=[
        ast.WhileStmt(
            cond=ast.BinaryOp("<", ast.Identifier("i"), ast.NumberLit(10)),
            body=ast.Block(statements=[
                ast.Assign(name="i", value=ast.BinaryOp("+", ast.Identifier("i"), ast.NumberLit(1))),
            ]),
        )
    ])


def test_unary_minus_parses():
    assert _expr("-5") == ast.UnaryOp(op="-", operand=ast.NumberLit(5))
    assert _expr("-x") == ast.UnaryOp(op="-", operand=ast.Identifier("x"))
    # `-x + y` should be `(-x) + y`, not `-(x + y)`.
    assert _expr("-x + y") == ast.BinaryOp(
        op="+",
        left=ast.UnaryOp(op="-", operand=ast.Identifier("x")),
        right=ast.Identifier("y"),
    )


def test_not_keyword_lower_precedence_than_comparison():
    # `not a == b` should parse as `not (a == b)`, matching Python.
    assert _expr("not a == b") == ast.UnaryOp(
        op="not",
        operand=ast.BinaryOp(op="==", left=ast.Identifier("a"), right=ast.Identifier("b")),
    )


def test_and_or_precedence_below_not():
    # `not a or b` should be `(not a) or b`.
    assert _expr("not a or b") == ast.BinaryOp(
        op="or",
        left=ast.UnaryOp(op="not", operand=ast.Identifier("a")),
        right=ast.Identifier("b"),
    )


def test_and_binds_tighter_than_or():
    # `a or b and c` → `a or (b and c)`.
    assert _expr("a or b and c") == ast.BinaryOp(
        op="or",
        left=ast.Identifier("a"),
        right=ast.BinaryOp(op="and", left=ast.Identifier("b"), right=ast.Identifier("c")),
    )


def test_boolean_and_null_literals():
    assert _expr("true") == ast.BoolLit(value=True)
    assert _expr("false") == ast.BoolLit(value=False)
    assert _expr("null") == ast.NullLit()


def test_float_literal_parses_to_float_value():
    e = _expr("3.14")
    assert isinstance(e, ast.NumberLit)
    assert e.value == 3.14
    assert isinstance(e.value, float)


def test_int_literal_stays_int():
    e = _expr("42")
    assert isinstance(e, ast.NumberLit)
    assert e.value == 42
    assert isinstance(e.value, int) and not isinstance(e.value, bool)


def test_compound_assign_carries_op():
    program = _strip_pos(_parse("x += 1"))
    stmt = program.body[0]
    assert isinstance(stmt, ast.Assign)
    assert stmt.op == "+"
    assert stmt.name == "x"
    assert stmt.value == ast.NumberLit(1)


def test_modulo_has_same_precedence_as_multiplication():
    # `a + b % c` → `a + (b % c)`.
    assert _expr("a + b % c") == ast.BinaryOp(
        op="+",
        left=ast.Identifier("a"),
        right=ast.BinaryOp(op="%", left=ast.Identifier("b"), right=ast.Identifier("c")),
    )


def test_full_example_functions_rot_parses_end_to_end():
    """The same program that's been our end-to-end golden since v1.0.0
    now parses to a full AST — funct + if/elseif/else chain + top-level
    call all represented as nodes."""
    import pathlib
    source = (pathlib.Path(__file__).resolve().parent.parent / "examples/functions.rot").read_text()
    program = _strip_pos(_parse(source))

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


def test_let_statement_parses_to_LetStmt():
    # v2.16.6: `let name = expr` parses into a dedicated ast.LetStmt node so
    # the interpreter can distinguish it from a plain Assign and bind locally.
    program = _strip_pos(_parse("let x = 42"))
    assert program == ast.Program(
        body=[ast.LetStmt(name="x", value=ast.NumberLit(value=42))]
    )


def test_let_with_complex_expression():
    program = _strip_pos(_parse("let total = a + b * 2"))
    assert isinstance(program.body[0], ast.LetStmt)
    let_stmt = program.body[0]
    assert let_stmt.name == "total"
    # a + (b * 2)
    assert let_stmt.value == ast.BinaryOp(
        op="+",
        left=ast.Identifier(name="a"),
        right=ast.BinaryOp(
            op="*", left=ast.Identifier(name="b"), right=ast.NumberLit(value=2)
        ),
    )


def test_let_rejects_compound_target_in_parser():
    with pytest.raises(ParserError):
        _parse("let obj.x = 1")
    with pytest.raises(ParserError):
        _parse("let xs[0] = 1")
    with pytest.raises(ParserError):
        _parse("let foo() = 1")


def test_let_requires_equals_sign():
    with pytest.raises(ParserError):
        _parse("let x 5")


def test_ast_nodes_default_line_col_to_zero():
    """v2.22.1: every AST node has optional `line` and `col` kwarg fields,
    defaulted to 0 (= unknown). Constructing a node WITHOUT passing them
    leaves both at 0 — so existing code that doesn't know about positions
    keeps working unchanged."""
    assert ast.Identifier(name="foo").line == 0
    assert ast.Identifier(name="foo").col == 0
    assert ast.NumberLit(value=42).line == 0
    assert ast.StringLit(value="x").col == 0
    assert ast.NullLit().line == 0
    assert ast.BreakStmt().line == 0
    assert ast.ContinueStmt().col == 0
    assert ast.Program().line == 0


def test_parser_populates_line_col_on_call_stmt():
    """v2.22.2: the parser stamps every AST node with the source position
    of its first token. The top-level ExprStmt and its Call should report
    line 1 col 1 (offsets are 1-indexed and counted from the start)."""
    program = _parse("cout(1)")
    stmt = program.body[0]
    assert isinstance(stmt, ast.ExprStmt)
    assert stmt.line == 1 and stmt.col == 1
    assert isinstance(stmt.expr, ast.Call)
    assert stmt.expr.line == 1 and stmt.expr.col == 1


def test_parser_populates_line_col_on_identifier():
    """An identifier reports the column it starts at, not 0."""
    program = _parse("    foo")
    stmt = program.body[0]
    assert isinstance(stmt, ast.ExprStmt)
    assert isinstance(stmt.expr, ast.Identifier)
    assert stmt.expr.line == 1
    # `foo` starts after four spaces of indentation; col is 1-indexed.
    assert stmt.expr.col == 5


def test_parser_populates_line_col_across_lines():
    """Multi-line source: line numbers should reflect the actual line."""
    program = _parse("x = 1\ny = 2\nz = 3")
    assert program.body[0].line == 1
    assert program.body[1].line == 2
    assert program.body[2].line == 3


def test_parser_populates_line_col_on_number_literal():
    program = _parse("42")
    assert isinstance(program.body[0].expr, ast.NumberLit)
    assert program.body[0].expr.line == 1
    assert program.body[0].expr.col == 1


def test_parser_populates_line_col_on_function_def():
    program = _parse("\nfunct hi() { }")
    assert isinstance(program.body[0], ast.FuncDef)
    assert program.body[0].line == 2  # second line
    assert program.body[0].col == 1


def test_parser_populates_line_col_on_binary_op_at_operator():
    """For a binary op, line/col should point at the OPERATOR — the
    invariant the interpreter relies on when reporting `cannot apply '+' ...`."""
    program = _parse("a + b")
    binop = program.body[0].expr
    assert isinstance(binop, ast.BinaryOp)
    assert binop.line == 1
    # `a + b` — col 3 is the `+`.
    assert binop.col == 3


# ---------- v2.22.4: parser errors carry line/col -----------------------


def test_unexpected_eof_in_atom_carries_line_col():
    """v2.22.4: EOF in atom position used to raise ParserError with line=0
    col=0 (suppressed by RotError prefix). Now points one column past the
    last consumed token."""
    with pytest.raises(ParserError) as exc_info:
        _parse("x = ")
    # The `=` is at column 3; EOF position is col 4 (one past the `=`).
    assert exc_info.value.line == 1
    assert exc_info.value.col > 0


def test_unterminated_block_error_carries_line_col():
    """Unterminated block points at the unclosed `{` so the user can see
    where the brace was opened."""
    with pytest.raises(ParserError) as exc_info:
        _parse("funct hi() { coutln(1)")
    err = exc_info.value
    assert err.line == 1
    # The `{` is at column 12 (after "funct hi() ").
    assert err.col == 12
    assert "unterminated block" in str(err)


def test_expected_token_at_eof_carries_line_col():
    """`_consume` at EOF should report the position past the last token,
    not 0:0."""
    with pytest.raises(ParserError) as exc_info:
        _parse("funct hi(")
    err = exc_info.value
    assert err.line == 1
    assert err.col > 0
