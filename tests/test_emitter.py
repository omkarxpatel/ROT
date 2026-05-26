"""Unit tests for the AST -> Python emitter (rot/emitter.py).

These exercise the emitter directly against handcrafted AST snippets,
complementing the end-to-end tests that go source -> emit -> exec.
"""

from rot import ast
from rot.emitter import Emitter


def _emit(*statements: ast.Statement) -> str:
    return Emitter().emit(ast.Program(body=list(statements)))


def test_emits_println_call():
    src = _emit(ast.ExprStmt(
        ast.Call(callee=ast.Identifier("coutln"), args=[ast.StringLit("hi")])
    ))
    assert src == "print('hi')"


def test_emits_cout_with_end_kwarg():
    src = _emit(ast.ExprStmt(
        ast.Call(callee=ast.Identifier("cout"), args=[ast.StringLit("hi")])
    ))
    assert src == 'print(\'hi\', end="")'


def test_emits_zero_arg_cout():
    src = _emit(ast.ExprStmt(ast.Call(callee=ast.Identifier("cout"), args=[])))
    assert src == 'print(end="")'


def test_emits_generic_call_for_non_print_callee():
    src = _emit(ast.ExprStmt(
        ast.Call(
            callee=ast.Identifier("hi"),
            args=[ast.NumberLit(10), ast.NumberLit(20)],
        )
    ))
    assert src == "hi(10, 20)"


def test_emits_function_definition_with_indented_body():
    src = _emit(ast.FuncDef(
        name="greet",
        params=["x", "y"],
        body=ast.Block(statements=[
            ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.Identifier("x")]))
        ]),
    ))
    assert src == "def greet(x,y):\n    print(x)"


def test_emits_empty_function_body_as_pass():
    src = _emit(ast.FuncDef(name="nada", params=[], body=ast.Block(statements=[])))
    assert src == "def nada():\n    pass"


def test_emits_if_elif_else_chain():
    src = _emit(ast.IfStmt(
        cond=ast.BinaryOp(">", ast.Identifier("x"), ast.Identifier("y")),
        then_block=ast.Block(statements=[
            ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.Identifier("x")]))
        ]),
        elif_branches=[
            ast.ElifBranch(
                cond=ast.BinaryOp("==", ast.Identifier("x"), ast.Identifier("y")),
                body=ast.Block(statements=[
                    ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.StringLit("same")]))
                ]),
            )
        ],
        else_block=ast.Block(statements=[
            ast.ExprStmt(ast.Call(callee=ast.Identifier("coutln"), args=[ast.Identifier("y")]))
        ]),
    ))
    assert src == (
        "if x > y:\n"
        "    print(x)\n"
        "elif x == y:\n"
        "    print('same')\n"
        "else:\n"
        "    print(y)"
    )


def test_binary_op_children_are_parenthesized_to_preserve_precedence():
    # AST is (1 + 2) * 3 — explicit precedence-overriding group.
    src = _emit(ast.ExprStmt(
        ast.BinaryOp(
            op="*",
            left=ast.BinaryOp(op="+", left=ast.NumberLit(1), right=ast.NumberLit(2)),
            right=ast.NumberLit(3),
        )
    ))
    assert src == "(1 + 2) * 3"


def test_flat_binary_op_does_not_add_unnecessary_parens():
    src = _emit(ast.ExprStmt(
        ast.BinaryOp(op="+", left=ast.NumberLit(1), right=ast.NumberLit(2))
    ))
    assert src == "1 + 2"


def test_emits_assignment():
    src = _emit(ast.Assign(name="x", value=ast.NumberLit(5)))
    assert src == "x = 5"


def test_emits_return_with_value():
    src = _emit(ast.Return(value=ast.Identifier("x")))
    assert src == "return x"


def test_emits_bare_return():
    src = _emit(ast.Return(value=None))
    assert src == "return"
