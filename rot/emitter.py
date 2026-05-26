"""AST -> Python source emitter.

Replaces the v1 token-to-string transpiler (rot/parser.py) on the active
compile path. Walks an `ast.Program` and produces a Python source string
with correct indentation and operator precedence preserved.
"""

from __future__ import annotations

from . import ast


_INDENT = "    "


class Emitter:
    def __init__(self) -> None:
        self.lines: list[str] = []
        self.depth = 0

    def emit(self, program: ast.Program) -> str:
        for stmt in program.body:
            self._emit_statement(stmt)
        return "\n".join(self.lines)

    def _emit_statement(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.ExprStmt):
            self._write(self._expr(stmt.expr))
        elif isinstance(stmt, ast.FuncDef):
            params = ",".join(stmt.params)
            self._write(f"def {stmt.name}({params}):")
            self._emit_block(stmt.body)
        elif isinstance(stmt, ast.IfStmt):
            self._emit_if(stmt)
        elif isinstance(stmt, ast.Assign):
            self._write(f"{stmt.name} = {self._expr(stmt.value)}")
        elif isinstance(stmt, ast.Return):
            if stmt.value is None:
                self._write("return")
            else:
                self._write(f"return {self._expr(stmt.value)}")
        else:
            raise NotImplementedError(f"emit: statement {type(stmt).__name__}")

    def _emit_if(self, stmt: ast.IfStmt) -> None:
        self._write(f"if {self._expr(stmt.cond)}:")
        self._emit_block(stmt.then_block)
        for branch in stmt.elif_branches:
            self._write(f"elif {self._expr(branch.cond)}:")
            self._emit_block(branch.body)
        if stmt.else_block is not None:
            self._write("else:")
            self._emit_block(stmt.else_block)

    def _emit_block(self, block: ast.Block) -> None:
        self.depth += 1
        if not block.statements:
            self._write("pass")
        else:
            for stmt in block.statements:
                self._emit_statement(stmt)
        self.depth -= 1

    def _expr(self, expr: ast.Expression) -> str:
        if isinstance(expr, ast.Identifier):
            return expr.name
        if isinstance(expr, ast.NumberLit):
            return str(expr.value)
        if isinstance(expr, ast.StringLit):
            return repr(expr.value)
        if isinstance(expr, ast.Call):
            return self._emit_call(expr)
        if isinstance(expr, ast.BinaryOp):
            left = self._expr_in_op(expr.left)
            right = self._expr_in_op(expr.right)
            return f"{left} {expr.op} {right}"
        raise NotImplementedError(f"emit: expression {type(expr).__name__}")

    def _emit_call(self, call: ast.Call) -> str:
        args = [self._expr(a) for a in call.args]
        # `cout` and `coutln` are the language's print builtins. cout
        # prints without a trailing newline; coutln uses Python's default.
        if isinstance(call.callee, ast.Identifier):
            if call.callee.name == "cout":
                if args:
                    return f'print({", ".join(args)}, end="")'
                return 'print(end="")'
            if call.callee.name == "coutln":
                return f"print({', '.join(args)})"
        callee = self._expr(call.callee)
        return f"{callee}({', '.join(args)})"

    def _expr_in_op(self, expr: ast.Expression) -> str:
        """Wrap a binary-op child in parens to preserve precedence."""
        if isinstance(expr, ast.BinaryOp):
            return f"({self._expr(expr)})"
        return self._expr(expr)

    def _write(self, text: str) -> None:
        self.lines.append(_INDENT * self.depth + text)
