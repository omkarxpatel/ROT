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
class RotFunctionValue:
    """A compiled function — what `LOAD_CONST` pushes when the VM sees
    a `FuncDef`. Carries the function's name (for error messages and
    stringification), parameter list, and the body chunk that gets a
    new frame when `CALL` fires.

    No closure environment yet — the VM looks up free names in the
    main frame's globals. Lexical closures land in a later Z.
    """

    name: str
    params: list[str] = field(default_factory=list)
    chunk: "Chunk | None" = None

    def __repr__(self) -> str:
        # Match the tree-walker's `<funct NAME>` rendering so cross-
        # engine output of `cout(foo)` matches once cout exists in
        # the VM.
        return f"<funct {self.name}>"


@dataclass
class RotClassValue:
    """A compiled class — what `LOAD_CONST` pushes when the VM sees a
    `ClassDef`. Methods are compiled at class-definition time (each
    is its own `RotFunctionValue`). Calling a class instantiates it
    and optionally runs `init`.
    """

    name: str
    methods: dict[str, RotFunctionValue] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<class {self.name}>"


@dataclass
class RotInstanceValue:
    """A class instance created by `CALL`-ing a `RotClassValue`. Holds
    the class reference (so member lookups can fall through to methods)
    and a mutable field dict.
    """

    cls: RotClassValue
    fields: dict[str, Any] = field(default_factory=dict)

    def __repr__(self) -> str:
        return f"<instance of {self.cls.name}>"


@dataclass
class RotBoundMethod:
    """A method already bound to its receiver instance. Returned by
    `GET_MEMBER` when the name resolves to one of the class's
    methods. `CALL` on a bound method prepends `this=instance` to
    the function's local env, then runs the method body.
    """

    instance: RotInstanceValue
    method: RotFunctionValue

    def __repr__(self) -> str:
        return f"<bound method {self.instance.cls.name}.{self.method.name}>"


@dataclass
class Chunk:
    """A compiled program. Holds the bytecode, the constant pool,
    and the name pool. Compact + JSON-serializable for the future
    bytecode pane in the playground.

    `code` entries are `(Op, *args)` tuples. Most ops have 0 or 1
    arg; future jump ops will have a single offset arg.

    `lines` is parallel to `code` — `lines[i]` is the 1-indexed
    source line that produced `code[i]`, or 0 if no source position
    was tracked (defensive/synthetic emits like fall-through
    `LOAD_NULL + RETURN_VALUE` at the end of a function body).
    """

    code: list[tuple] = field(default_factory=list)
    lines: list[int] = field(default_factory=list)
    constants: list[Any] = field(default_factory=list)
    names: list[str] = field(default_factory=list)

    def emit(self, op: Op, *args: int, line: int = 0) -> int:
        """Append an instruction and return its offset in `code`.

        `line` is the 1-indexed source line this instruction belongs
        to — passed in by `Compiler._emit` from
        `Compiler._current_line`, which is set per-statement.
        """
        self.code.append((op, *args))
        self.lines.append(line)
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

    def to_dict(self) -> dict:
        """JSON-safe dump of the chunk. Used by the playground bridge
        to expose compiled bytecode to the browser side.

        Instructions become `[op_name, *args]`; constants are
        primitives where possible, dicts for nested function values
        (with their own chunk dumped recursively). `lines` is the
        per-instruction source-line array — the UI uses it to filter
        the bytecode pane down to instructions for the active step.
        """
        return {
            "code": [_instr_to_dict(instr) for instr in self.code],
            "lines": list(self.lines),
            "constants": [_const_to_dict(c) for c in self.constants],
            "names": list(self.names),
        }

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
        # Source line currently being compiled. Set by `_compile_stmt`
        # from `stmt.line` and stamped onto every emit via `_emit` so
        # the playground's bytecode pane can filter to the current
        # statement.
        self._current_line: int = 0

    def _emit(self, op: Op, *args: int) -> int:
        """Compile-time emit wrapper. Stamps the current statement's
        source line onto the instruction so the playground can
        highlight only this statement's bytecode."""
        return self.chunk.emit(op, *args, line=self._current_line)

    def compile(self, program: ast.Program) -> Chunk:
        for stmt in program.body:
            self._compile_stmt(stmt)
        self._emit(Op.RETURN)
        return self.chunk

    # ─── Statements ────────────────────────────────────────────────

    def _compile_stmt(self, stmt: ast.Statement) -> None:
        prior_line = self._current_line
        stmt_line = getattr(stmt, "line", 0)
        if stmt_line:
            self._current_line = stmt_line
        try:
            self._compile_stmt_dispatch(stmt)
        finally:
            self._current_line = prior_line

    def _compile_stmt_dispatch(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.ExprStmt):
            self._compile_expr(stmt.expr)
            # Discard the value — ROT statements don't propagate values.
            self._emit(Op.POP)
            return
        if isinstance(stmt, ast.Assign):
            assign_op = getattr(stmt, "op", "=")
            if assign_op == "=":
                self._compile_expr(stmt.value)
                idx = self.chunk.add_name(stmt.name)
                self._emit(Op.STORE_NAME, idx)
                return
            # Compound: `x op= value` → LOAD_NAME, value, op, STORE_NAME.
            bin_op = _BIN_OP_MAP.get(assign_op)
            if bin_op is None:
                raise NotImplementedError(
                    f"codegen: compound assign {assign_op!r} not supported"
                )
            idx = self.chunk.add_name(stmt.name)
            self._emit(Op.LOAD_NAME, idx)
            self._compile_expr(stmt.value)
            self._emit(bin_op)
            self._emit(Op.STORE_NAME, idx)
            return
        if isinstance(stmt, ast.LetStmt):
            # For now Let and Assign generate the same bytecode. The
            # distinction (Let = fresh local, no chain-walk) matters
            # for closures and is wired in when STORE_LOCAL lands.
            self._compile_expr(stmt.value)
            idx = self.chunk.add_name(stmt.name)
            self._emit(Op.STORE_NAME, idx)
            return
        if isinstance(stmt, ast.IfStmt):
            self._compile_if(stmt)
            return
        if isinstance(stmt, ast.WhileStmt):
            self._compile_while(stmt)
            return
        if isinstance(stmt, ast.ForStmt):
            self._compile_for(stmt)
            return
        if isinstance(stmt, ast.BreakStmt):
            if not self._loop_stack:
                raise InterpreterError("`break` outside of a loop")
            idx = self._emit(Op.JUMP, 0)
            self._loop_stack[-1]["break_jumps"].append(idx)
            return
        if isinstance(stmt, ast.ContinueStmt):
            if not self._loop_stack:
                raise InterpreterError("`continue` outside of a loop")
            self._emit(Op.JUMP, self._loop_stack[-1]["start"])
            return
        if isinstance(stmt, ast.FuncDef):
            self._compile_func_def(stmt)
            return
        if isinstance(stmt, ast.ClassDef):
            self._compile_class_def(stmt)
            return
        if isinstance(stmt, ast.MemberAssign):
            assign_op = getattr(stmt, "op", "=")
            idx = self.chunk.add_name(stmt.member)
            if assign_op == "=":
                self._compile_expr(stmt.target)
                self._compile_expr(stmt.value)
                self._emit(Op.SET_MEMBER, idx)
                return
            # Compound: `target.member op= value`. Emit:
            #   [target] DUP [target,target] GET_MEMBER member
            #   [target, current] [value] op [target, current op value]
            #   SET_MEMBER member
            bin_op = _BIN_OP_MAP.get(assign_op)
            if bin_op is None:
                raise NotImplementedError(
                    f"codegen: compound member assign {assign_op!r}"
                    " not supported"
                )
            self._compile_expr(stmt.target)
            self._emit(Op.DUP)
            self._emit(Op.GET_MEMBER, idx)
            self._compile_expr(stmt.value)
            self._emit(bin_op)
            self._emit(Op.SET_MEMBER, idx)
            return
        if isinstance(stmt, ast.Return):
            if stmt.value is not None:
                self._compile_expr(stmt.value)
            else:
                self._emit(Op.LOAD_NULL)
            self._emit(Op.RETURN_VALUE)
            return
        if isinstance(stmt, ast.TryCatch):
            self._compile_try_catch(stmt)
            return
        if isinstance(stmt, ast.ThrowStmt):
            self._compile_expr(stmt.value)
            self._emit(Op.RAISE)
            return
        if isinstance(stmt, ast.IndexAssign):
            # `xs[i] = v` — currently supports plain `=`. Compound
            # assigns (`xs[i] += 1`) will land alongside the
            # tree-walker's compound logic in a later Z.
            if getattr(stmt, "op", "=") != "=":
                raise NotImplementedError(
                    f"codegen: compound index assign {stmt.op!r}"
                    " not yet supported"
                )
            self._compile_expr(stmt.target)
            self._compile_expr(stmt.index)
            self._compile_expr(stmt.value)
            self._emit(Op.SET_INDEX)
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
        skip_idx = self._emit(Op.JUMP_IF_FALSE, 0)
        self._compile_block(stmt.then_block)
        end_jumps.append(self._emit(Op.JUMP, 0))
        self.chunk.patch_jump(skip_idx, len(self.chunk.code))

        # Each elif.
        for branch in stmt.elif_branches:
            self._compile_expr(branch.cond)
            skip_idx = self._emit(Op.JUMP_IF_FALSE, 0)
            self._compile_block(branch.body)
            end_jumps.append(self._emit(Op.JUMP, 0))
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
        self._emit(Op.DUP)
        end_idx = self._emit(jump_on, 0)
        self._emit(Op.POP)
        self._compile_expr(expr.right)
        self.chunk.patch_jump(end_idx, len(self.chunk.code))

    def _compile_for(self, stmt: ast.ForStmt) -> None:
        """Emit a `for x in <iter> { body }` loop:

            compile iter expression
            GET_ITER                         # iter on stack
          loop_start:
            ITER_NEXT → end                  # peek iter; if exhausted, jump
                                             # to end (iter stays on stack)
            STORE_NAME x                     # bind the next value to x
            body...
            JUMP            → loop_start
          end:
            POP                              # discard the now-exhausted iter

        `break` inside the body jumps to `end` (the POP at end cleans
        up the iter for both paths). `continue` jumps to `loop_start`
        which re-runs `ITER_NEXT` correctly because the iter is still
        on the stack.
        """
        self._compile_expr(stmt.iter)
        self._emit(Op.GET_ITER)
        loop_start = len(self.chunk.code)
        iter_jump_idx = self._emit(Op.ITER_NEXT, 0)
        name_idx = self.chunk.add_name(stmt.var)
        self._emit(Op.STORE_NAME, name_idx)

        ctx = {"start": loop_start, "break_jumps": []}
        self._loop_stack.append(ctx)
        try:
            self._compile_block(stmt.body)
        finally:
            self._loop_stack.pop()

        self._emit(Op.JUMP, loop_start)
        # `end` is the location of the POP — both ITER_NEXT-exhausted
        # and `break` target this IP so the iter gets cleaned up
        # exactly once.
        end_ip = len(self.chunk.code)
        self._emit(Op.POP)
        self.chunk.patch_jump(iter_jump_idx, end_ip)
        for idx in ctx["break_jumps"]:
            self.chunk.patch_jump(idx, end_ip)

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
        skip_idx = self._emit(Op.JUMP_IF_FALSE, 0)

        ctx = {"start": loop_start, "break_jumps": []}
        self._loop_stack.append(ctx)
        try:
            self._compile_block(stmt.body)
        finally:
            self._loop_stack.pop()

        self._emit(Op.JUMP, loop_start)
        end_ip = len(self.chunk.code)
        self.chunk.patch_jump(skip_idx, end_ip)
        for idx in ctx["break_jumps"]:
            self.chunk.patch_jump(idx, end_ip)

    # ─── Expressions ───────────────────────────────────────────────

    def _compile_expr(self, expr: ast.Expression) -> None:
        if isinstance(expr, ast.NumberLit):
            idx = self.chunk.add_const(expr.value)
            self._emit(Op.LOAD_CONST, idx)
            return
        if isinstance(expr, ast.StringLit):
            idx = self.chunk.add_const(expr.value)
            self._emit(Op.LOAD_CONST, idx)
            return
        if isinstance(expr, ast.BoolLit):
            self._emit(Op.LOAD_TRUE if expr.value else Op.LOAD_FALSE)
            return
        if isinstance(expr, ast.NullLit):
            self._emit(Op.LOAD_NULL)
            return
        if isinstance(expr, ast.Identifier):
            idx = self.chunk.add_name(expr.name)
            self._emit(Op.LOAD_NAME, idx)
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
            self._emit(op)
            return
        if isinstance(expr, ast.UnaryOp):
            self._compile_expr(expr.operand)
            if expr.op == "-":
                self._emit(Op.NEG)
                return
            if expr.op == "not":
                self._emit(Op.NOT)
                return
            raise NotImplementedError(
                f"codegen: unary op {expr.op!r} not yet supported"
            )
        if isinstance(expr, ast.ListLit):
            for elem in expr.elements:
                self._compile_expr(elem)
            self._emit(Op.BUILD_LIST, len(expr.elements))
            return
        if isinstance(expr, ast.DictLit):
            for (k, v) in expr.pairs:
                self._compile_expr(k)
                self._compile_expr(v)
            self._emit(Op.BUILD_DICT, len(expr.pairs))
            return
        if isinstance(expr, ast.Index):
            self._compile_expr(expr.target)
            self._compile_expr(expr.index)
            self._emit(Op.GET_INDEX)
            return
        if isinstance(expr, ast.MemberAccess):
            self._compile_expr(expr.target)
            idx = self.chunk.add_name(expr.member)
            self._emit(Op.GET_MEMBER, idx)
            return
        if isinstance(expr, ast.Call):
            # Stack at the time of CALL: [function, arg1, ..., argN].
            self._compile_expr(expr.callee)
            for arg in expr.args:
                self._compile_expr(arg)
            self._emit(Op.CALL, len(expr.args))
            return
        raise NotImplementedError(
            f"codegen: expression {type(expr).__name__!r} not yet supported"
        )

    def _compile_func_def(self, stmt: ast.FuncDef) -> None:
        """Compile a `funct name(p1 | p2) { body }`:

        1. Compile the body into its OWN chunk via a fresh `Compiler`
           (params get bound by `CALL` when invoked, so we don't emit
           any setup for them here).
        2. The body's chunk must end with a `RETURN_VALUE` —
           functions that fall off the end implicitly return `null`,
           so we append `LOAD_NULL; RETURN_VALUE` defensively (no
           harm if a real `Return` statement already emitted one,
           since IP will have left the chunk before reaching it).
        3. Wrap into a `RotFunctionValue`, add it to the outer
           chunk's constant pool, and emit `LOAD_CONST + STORE_NAME`
           so the function value lands in the surrounding env.
        """
        body_compiler = Compiler()
        body_compiler._compile_block(stmt.body)
        body_compiler._emit(Op.LOAD_NULL)
        body_compiler._emit(Op.RETURN_VALUE)

        func_val = RotFunctionValue(
            name=stmt.name,
            params=list(stmt.params),
            chunk=body_compiler.chunk,
        )
        const_idx = self.chunk.add_const(func_val)
        self._emit(Op.LOAD_CONST, const_idx)
        name_idx = self.chunk.add_name(stmt.name)
        self._emit(Op.STORE_NAME, name_idx)

    def _compile_try_catch(self, stmt: ast.TryCatch) -> None:
        """Emit:

            BEGIN_TRY → catch_ip
            ... try body ...
            END_TRY
            JUMP   → end
          catch_ip:
            STORE_NAME catch_var       (the thrown value is on top)
            ... catch body ...
          end:

        `finally` blocks need careful unwinding to run on uncaught
        propagation too — deferred. If the AST has one, raise.
        """
        if stmt.finally_block is not None:
            raise NotImplementedError(
                "codegen: try/finally not yet supported in the VM"
            )
        begin_idx = self._emit(Op.BEGIN_TRY, 0)
        self._compile_block(stmt.try_block)
        self._emit(Op.END_TRY)
        end_jump_idx = self._emit(Op.JUMP, 0)
        # catch entry point
        catch_ip = len(self.chunk.code)
        self.chunk.patch_jump(begin_idx, catch_ip)
        name_idx = self.chunk.add_name(stmt.catch_var)
        self._emit(Op.STORE_NAME, name_idx)
        self._compile_block(stmt.catch_block)
        end_ip = len(self.chunk.code)
        self.chunk.patch_jump(end_jump_idx, end_ip)

    def _compile_class_def(self, stmt: ast.ClassDef) -> None:
        """Compile each method into its own `RotFunctionValue`, wrap
        them into a `RotClassValue`, and store it in the surrounding
        env via `LOAD_CONST + STORE_NAME` — same shape as a top-level
        function definition."""
        methods: dict[str, RotFunctionValue] = {}
        for member in stmt.methods:
            body_compiler = Compiler()
            body_compiler._compile_block(member.body)
            body_compiler._emit(Op.LOAD_NULL)
            body_compiler._emit(Op.RETURN_VALUE)
            methods[member.name] = RotFunctionValue(
                name=member.name,
                params=list(member.params),
                chunk=body_compiler.chunk,
            )
        class_val = RotClassValue(name=stmt.name, methods=methods)
        const_idx = self.chunk.add_const(class_val)
        self._emit(Op.LOAD_CONST, const_idx)
        name_idx = self.chunk.add_name(stmt.name)
        self._emit(Op.STORE_NAME, name_idx)


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


def _instr_to_dict(instr: tuple) -> list:
    """Convert an opcode tuple `(Op, *args)` into a JSON-safe list
    `[op_name, *args]`."""
    op = instr[0]
    name = op.name if hasattr(op, "name") else str(op)
    return [name, *instr[1:]]


def _const_to_dict(value):
    """Convert a constant pool entry to JSON-safe form. Primitives
    pass through; `RotFunctionValue` becomes a dict with the nested
    chunk dumped recursively; `RotClassValue` becomes a dict with
    its methods recursively dumped."""
    if isinstance(value, RotFunctionValue):
        return {
            "__type__": "RotFunctionValue",
            "name": value.name,
            "params": list(value.params),
            "chunk": value.chunk.to_dict() if value.chunk is not None else None,
        }
    if isinstance(value, RotClassValue):
        return {
            "__type__": "RotClassValue",
            "name": value.name,
            "methods": {
                mname: _const_to_dict(m) for mname, m in value.methods.items()
            },
        }
    return value


__all__ = [
    "Chunk",
    "Compiler",
    "RotFunctionValue",
    "RotClassValue",
    "RotInstanceValue",
    "RotBoundMethod",
    "InterpreterError",
]
