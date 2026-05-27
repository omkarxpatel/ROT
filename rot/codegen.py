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

    def patch_jump(self, idx: int, target: int) -> None:
        """Replace the placeholder target on a previously-emitted jump
        with `target` (an absolute IP). Used by control-flow codegen
        which emits the jump *before* it knows where to land."""
        op = self.code[idx][0]
        self.code[idx] = (op, target)


class Compiler:
    """Walks an `ast.Program` and emits bytecode into a `Chunk`."""

    def __init__(self) -> None:
        self.chunk = Chunk()
        # Stack of active loop contexts for `break` / `continue`. Each
        # entry: {"start": IP_to_jump_back_to,
        #         "break_jumps": [idxs to patch when loop ends]}.
        self._loop_stack: list[dict] = []

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
        if isinstance(stmt, ast.IfStmt):
            self._compile_if(stmt)
            return
        if isinstance(stmt, ast.WhileStmt):
            self._compile_while(stmt)
            return
        if isinstance(stmt, ast.BreakStmt):
            if not self._loop_stack:
                raise InterpreterError("`break` outside of a loop")
            idx = self.chunk.emit(Op.JUMP, 0)
            self._loop_stack[-1]["break_jumps"].append(idx)
            return
        if isinstance(stmt, ast.ContinueStmt):
            if not self._loop_stack:
                raise InterpreterError("`continue` outside of a loop")
            self.chunk.emit(Op.JUMP, self._loop_stack[-1]["start"])
            return
        raise NotImplementedError(
            f"codegen: statement {type(stmt).__name__!r} not yet supported"
        )

    def _compile_block(self, block: "ast.Block") -> None:
        for stmt in block.statements:
            self._compile_stmt(stmt)

    def _compile_if(self, stmt: ast.IfStmt) -> None:
        """Emit jump-based if / elseif / else.

        Layout for `if (c1) {b1} elseif (c2) {b2} else {b3}`:

            compile c1
            JUMP_IF_FALSE → try_c2
            compile b1
            JUMP            → end          (added to `end_jumps`)
          try_c2:
            compile c2
            JUMP_IF_FALSE → else_block
            compile b2
            JUMP            → end          (added to `end_jumps`)
          else_block:
            compile b3
          end:                              (patches every `end_jumps`)
        """
        end_jumps: list[int] = []

        # First branch (the leading `if`).
        self._compile_expr(stmt.cond)
        skip_idx = self.chunk.emit(Op.JUMP_IF_FALSE, 0)
        self._compile_block(stmt.then_block)
        end_jumps.append(self.chunk.emit(Op.JUMP, 0))
        self.chunk.patch_jump(skip_idx, len(self.chunk.code))

        # Each elif.
        for branch in stmt.elif_branches:
            self._compile_expr(branch.cond)
            skip_idx = self.chunk.emit(Op.JUMP_IF_FALSE, 0)
            self._compile_block(branch.body)
            end_jumps.append(self.chunk.emit(Op.JUMP, 0))
            self.chunk.patch_jump(skip_idx, len(self.chunk.code))

        # Optional else.
        if stmt.else_block is not None:
            self._compile_block(stmt.else_block)

        # All taken-branch jumps land here.
        end_ip = len(self.chunk.code)
        for idx in end_jumps:
            self.chunk.patch_jump(idx, end_ip)

    def _compile_short_circuit(
        self, expr: ast.BinaryOp, *, jump_on: Op
    ) -> None:
        """Emit short-circuit bytecode for `and` / `or`.

        For `a and b` (jump_on=JUMP_IF_FALSE) the layout is:

            compile a
            DUP                       # keep `a` for the short-circuit case
            JUMP_IF_FALSE → end       # pops one copy; if falsy, a is the result
            POP                       # truthy path: discard `a`, evaluate `b`
            compile b
            end:                      # stack: [a] (short) or [b] (full)

        `or` swaps JUMP_IF_FALSE → JUMP_IF_TRUE. Both produce the
        Python-style "return the operand, not the boolean" semantics
        the tree-walker already implements.
        """
        self._compile_expr(expr.left)
        self.chunk.emit(Op.DUP)
        end_idx = self.chunk.emit(jump_on, 0)
        self.chunk.emit(Op.POP)
        self._compile_expr(expr.right)
        self.chunk.patch_jump(end_idx, len(self.chunk.code))

    def _compile_while(self, stmt: ast.WhileStmt) -> None:
        """Emit a back-edge loop:

            loop_start:
              compile cond
              JUMP_IF_FALSE → end
              compile body
              JUMP            → loop_start
            end:                              (patches break + skip)

        `break` JUMPs are collected on the loop context and patched
        to `end`; `continue` JUMPs go straight to `loop_start`.
        """
        loop_start = len(self.chunk.code)
        self._compile_expr(stmt.cond)
        skip_idx = self.chunk.emit(Op.JUMP_IF_FALSE, 0)

        ctx = {"start": loop_start, "break_jumps": []}
        self._loop_stack.append(ctx)
        try:
            self._compile_block(stmt.body)
        finally:
            self._loop_stack.pop()

        self.chunk.emit(Op.JUMP, loop_start)
        end_ip = len(self.chunk.code)
        self.chunk.patch_jump(skip_idx, end_ip)
        for idx in ctx["break_jumps"]:
            self.chunk.patch_jump(idx, end_ip)

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
            if expr.op == "and":
                self._compile_short_circuit(expr, jump_on=Op.JUMP_IF_FALSE)
                return
            if expr.op == "or":
                self._compile_short_circuit(expr, jump_on=Op.JUMP_IF_TRUE)
                return
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
            if expr.op == "not":
                self.chunk.emit(Op.NOT)
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
    "==": Op.EQ,
    "!=": Op.NE,
    "<": Op.LT,
    "<=": Op.LE,
    ">": Op.GT,
    ">=": Op.GE,
}


__all__ = ["Chunk", "Compiler", "InterpreterError"]
