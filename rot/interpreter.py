"""Tree-walking interpreter — executes an `ast.Program` directly.

This is the v2.0.0 cut: `exec()` is gone. The interpreter walks the AST,
maintains a lexically-scoped environment, and runs the program's
semantics without producing Python source.

`cout` and `coutln` are bound in the global environment as Python
callables — they're the language's only built-ins so far.
"""

from __future__ import annotations

from typing import Any, Callable

from . import ast
from .errors import InterpreterError


_BINARY_OPS: dict[str, Callable[[Any, Any], Any]] = {
    "+":  lambda a, b: a + b,
    "-":  lambda a, b: a - b,
    "*":  lambda a, b: a * b,
    "/":  lambda a, b: a / b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


class Environment:
    """A lexically-scoped variable binding map."""

    def __init__(self, parent: "Environment | None" = None) -> None:
        self.values: dict[str, Any] = {}
        self.parent = parent

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise InterpreterError(f"name {name!r} is not defined")

    def set(self, name: str, value: Any) -> None:
        self.values[name] = value


class RotFunction:
    """A user-defined function: a `funct` declaration bound to a closure env."""

    def __init__(self, decl: ast.FuncDef, closure: Environment) -> None:
        self.decl = decl
        self.closure = closure

    def call(self, args: list[Any], interpreter: "Interpreter") -> None:
        if len(args) != len(self.decl.params):
            raise InterpreterError(
                f"function {self.decl.name!r} takes {len(self.decl.params)} "
                f"argument(s), got {len(args)}"
            )
        local = Environment(parent=self.closure)
        for param, value in zip(self.decl.params, args):
            local.set(param, value)

        prior = interpreter.env
        interpreter.env = local
        try:
            interpreter._execute_block(self.decl.body)
        finally:
            interpreter.env = prior


class Interpreter:
    def __init__(self) -> None:
        self.env = Environment()
        self.env.set("cout", _builtin_cout)
        self.env.set("coutln", _builtin_coutln)

    def execute(self, program: ast.Program) -> None:
        for stmt in program.body:
            self._execute_statement(stmt)

    def _execute_statement(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.ExprStmt):
            self._evaluate(stmt.expr)
            return
        if isinstance(stmt, ast.FuncDef):
            self.env.set(stmt.name, RotFunction(stmt, self.env))
            return
        if isinstance(stmt, ast.IfStmt):
            self._execute_if(stmt)
            return
        raise InterpreterError(f"cannot execute statement {type(stmt).__name__}")

    def _execute_if(self, stmt: ast.IfStmt) -> None:
        if self._evaluate(stmt.cond):
            self._execute_block(stmt.then_block)
            return
        for branch in stmt.elif_branches:
            if self._evaluate(branch.cond):
                self._execute_block(branch.body)
                return
        if stmt.else_block is not None:
            self._execute_block(stmt.else_block)

    def _execute_block(self, block: ast.Block) -> None:
        for stmt in block.statements:
            self._execute_statement(stmt)

    def _evaluate(self, expr: ast.Expression) -> Any:
        if isinstance(expr, ast.NumberLit):
            return expr.value
        if isinstance(expr, ast.StringLit):
            return expr.value
        if isinstance(expr, ast.Identifier):
            return self.env.get(expr.name)
        if isinstance(expr, ast.Call):
            return self._evaluate_call(expr)
        if isinstance(expr, ast.BinaryOp):
            left = self._evaluate(expr.left)
            right = self._evaluate(expr.right)
            op = _BINARY_OPS.get(expr.op)
            if op is None:
                raise InterpreterError(f"unknown operator {expr.op!r}")
            return op(left, right)
        raise InterpreterError(f"cannot evaluate {type(expr).__name__}")

    def _evaluate_call(self, expr: ast.Call) -> Any:
        callee = self._evaluate(expr.callee)
        args = [self._evaluate(a) for a in expr.args]
        if isinstance(callee, RotFunction):
            callee.call(args, self)
            return None
        if callable(callee):
            return callee(*args)
        raise InterpreterError(f"not callable: {callee!r}")


def _builtin_cout(*args: Any) -> None:
    print(*args, sep="", end="")


def _builtin_coutln(*args: Any) -> None:
    print(*args, sep="")
