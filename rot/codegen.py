"""AST → bytecode compiler for the ROT VM (Milestone 2).

The compiler walks a parsed `ast.Program` and produces a `Chunk`
containing bytecode instructions, a constant pool, and a name pool.

This is the foundation Z (v2.27.0). The visitor currently handles
literals, identifiers, simple assigns, let-bindings, and binary `+`
`-` `*` `/` `%` plus unary `-`. Everything else raises
`NotImplementedError`; later Z's add control flow, function calls,
collections, etc.

The tree-walking `Interpreter` is the reference implementation —
this VM is an alternative engine, opt-in via `Compiler(use_vm=True)`
once the CLI wires it up (planned for a later Z).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import ast
from .errors import InterpreterError
from .opcodes import Op


@dataclass
class Chunk:
    """A compiled program. Holds the bytecode, the constant pool,
    and the name pool. Compact + JSON-serializable for the future
    bytecode pane in the playground.

    `code` entries are `(Op, *args)` tuples. Most ops have 0 or 1
    arg; future jump ops will have a single offset arg.
    """

    code: list[tuple] = field(default_factory=list)
    constants: list[Any] = field(default_factory=list)
    names: list[str] = field(default_factory=list)

    def emit(self, op: Op, *args: int) -> int:
        """Append an instruction and return its offset in `code`."""
        self.code.append((op, *args))
        return len(self.code) - 1

    def add_const(self, value: Any) -> int:
        """Add a constant to the pool (deduplicating by `is` then
        `==`) and return its index."""
        for i, v in enumerate(self.constants):
            if v is value or v == value:
                return i
        self.constants.append(value)
        return len(self.constants) - 1

    def add_name(self, name: str) -> int:
        """Add a name to the name pool (deduplicated) and return its
        index."""
        for i, n in enumerate(self.names):
            if n == name:
                return i
        self.names.append(name)
        return len(self.names) - 1


class Compiler:
    """Walks an `ast.Program` and emits bytecode into a `Chunk`."""

    def __init__(self) -> None:
        self.chunk = Chunk()

    def compile(self, program: ast.Program) -> Chunk:
        for stmt in program.body:
            self._compile_stmt(stmt)
        self.chunk.emit(Op.RETURN)
        return self.chunk

    # ─── Statements ────────────────────────────────────────────────

    def _compile_stmt(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.ExprStmt):
            self._compile_expr(stmt.expr)
            # Discard the value — ROT statements don't propagate values.
            self.chunk.emit(Op.POP)
            return
        if isinstance(stmt, ast.Assign):
            self._compile_expr(stmt.value)
            idx = self.chunk.add_name(stmt.name)
            self.chunk.emit(Op.STORE_NAME, idx)
            return
        if isinstance(stmt, ast.LetStmt):
            # For now Let and Assign generate the same bytecode. The
            # distinction (Let = fresh local, no chain-walk) matters
            # for closures and is wired in when STORE_LOCAL lands.
            self._compile_expr(stmt.value)
            idx = self.chunk.add_name(stmt.name)
            self.chunk.emit(Op.STORE_NAME, idx)
            return
        raise NotImplementedError(
            f"codegen: statement {type(stmt).__name__!r} not yet supported"
        )

    # ─── Expressions ───────────────────────────────────────────────

    def _compile_expr(self, expr: ast.Expression) -> None:
        if isinstance(expr, ast.NumberLit):
            idx = self.chunk.add_const(expr.value)
            self.chunk.emit(Op.LOAD_CONST, idx)
            return
        if isinstance(expr, ast.StringLit):
            idx = self.chunk.add_const(expr.value)
            self.chunk.emit(Op.LOAD_CONST, idx)
            return
        if isinstance(expr, ast.BoolLit):
            self.chunk.emit(Op.LOAD_TRUE if expr.value else Op.LOAD_FALSE)
            return
        if isinstance(expr, ast.NullLit):
            self.chunk.emit(Op.LOAD_NULL)
            return
        if isinstance(expr, ast.Identifier):
            idx = self.chunk.add_name(expr.name)
            self.chunk.emit(Op.LOAD_NAME, idx)
            return
        if isinstance(expr, ast.BinaryOp):
            self._compile_expr(expr.left)
            self._compile_expr(expr.right)
            op = _BIN_OP_MAP.get(expr.op)
            if op is None:
                raise NotImplementedError(
                    f"codegen: binary op {expr.op!r} not yet supported"
                )
            self.chunk.emit(op)
            return
        if isinstance(expr, ast.UnaryOp):
            self._compile_expr(expr.operand)
            if expr.op == "-":
                self.chunk.emit(Op.NEG)
                return
            raise NotImplementedError(
                f"codegen: unary op {expr.op!r} not yet supported"
            )
        raise NotImplementedError(
            f"codegen: expression {type(expr).__name__!r} not yet supported"
        )


_BIN_OP_MAP: dict[str, Op] = {
    "+": Op.ADD,
    "-": Op.SUB,
    "*": Op.MUL,
    "/": Op.DIV,
    "%": Op.MOD,
}


__all__ = ["Chunk", "Compiler", "InterpreterError"]
