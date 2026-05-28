"""Stack-based VM for executing bytecode produced by `rot.codegen`.

This is the M2 foundation Z. The dispatch loop currently handles
literals, variables, basic arithmetic, and the RETURN halt opcode —
enough to run programs like `x = 1 + 2`. Each subsequent Z extends
the dispatch with one or two opcodes plus the codegen + tests.

The VM intentionally mirrors `Interpreter`'s value semantics where
they overlap (e.g. `+` coerces to string when either side is a
string). The tree-walking interpreter remains the reference; the
test suite cross-checks the VM against it as new opcodes land.
"""

from __future__ import annotations

from typing import Any

from .codegen import Chunk
from .errors import InterpreterError
from .opcodes import Op


def _plus(a: Any, b: Any) -> Any:
    """Mirror `Interpreter`'s `+`: string-coerce when either side is a
    string. Otherwise plain numeric addition (and Python raises
    TypeError on incompatible types, which we wrap as InterpreterError
    at the dispatch site)."""
    if isinstance(a, str) or isinstance(b, str):
        return _stringify(a) + _stringify(b)
    return a + b


def _stringify(value: Any) -> str:
    """Compact ROT-style stringifier — for now just a thin wrapper so
    string-coercion in `_plus` matches the interpreter for primitive
    types. Will eventually share code with `rot.builtins._stringify`."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    return str(value)


class VM:
    """Executes a `Chunk` on a value stack with a global env dict."""

    def __init__(self, chunk: Chunk) -> None:
        self.chunk = chunk
        self.stack: list[Any] = []
        self.env: dict[str, Any] = {}
        self.ip: int = 0

    def run(self) -> None:
        code = self.chunk.code
        while self.ip < len(code):
            instr = code[self.ip]
            self.ip += 1
            op = instr[0]

            if op == Op.LOAD_CONST:
                self.stack.append(self.chunk.constants[instr[1]])
                continue
            if op == Op.LOAD_NULL:
                self.stack.append(None)
                continue
            if op == Op.LOAD_TRUE:
                self.stack.append(True)
                continue
            if op == Op.LOAD_FALSE:
                self.stack.append(False)
                continue
            if op == Op.POP:
                self.stack.pop()
                continue
            if op == Op.DUP:
                self.stack.append(self.stack[-1])
                continue
            if op == Op.LOAD_NAME:
                name = self.chunk.names[instr[1]]
                if name not in self.env:
                    raise InterpreterError(f"name {name!r} is not defined")
                self.stack.append(self.env[name])
                continue
            if op == Op.STORE_NAME:
                name = self.chunk.names[instr[1]]
                self.env[name] = self.stack.pop()
                continue
            if op == Op.ADD:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(_plus(a, b))
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.SUB:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a - b)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.MUL:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a * b)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.DIV:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a / b)
                except ZeroDivisionError:
                    raise InterpreterError("division by zero")
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.MOD:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a % b)
                except ZeroDivisionError:
                    raise InterpreterError("modulo by zero")
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.NEG:
                a = self.stack.pop()
                try:
                    self.stack.append(-a)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.EQ:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a == b)
                continue
            if op == Op.NE:
                b = self.stack.pop()
                a = self.stack.pop()
                self.stack.append(a != b)
                continue
            if op == Op.LT:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a < b)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.LE:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a <= b)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.GT:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a > b)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.GE:
                b = self.stack.pop()
                a = self.stack.pop()
                try:
                    self.stack.append(a >= b)
                except TypeError as e:
                    raise InterpreterError(str(e))
                continue
            if op == Op.NOT:
                a = self.stack.pop()
                self.stack.append(not a)
                continue
            if op == Op.JUMP:
                self.ip = instr[1]
                continue
            if op == Op.JUMP_IF_FALSE:
                val = self.stack.pop()
                if not val:
                    self.ip = instr[1]
                continue
            if op == Op.JUMP_IF_TRUE:
                val = self.stack.pop()
                if val:
                    self.ip = instr[1]
                continue
            if op == Op.BUILD_LIST:
                n = instr[1]
                if n == 0:
                    self.stack.append([])
                else:
                    items = self.stack[-n:]
                    del self.stack[-n:]
                    self.stack.append(list(items))
                continue
            if op == Op.BUILD_DICT:
                n = instr[1]
                if n == 0:
                    self.stack.append({})
                else:
                    flat = self.stack[-2 * n:]
                    del self.stack[-2 * n:]
                    d: dict = {}
                    for i in range(0, len(flat), 2):
                        d[flat[i]] = flat[i + 1]
                    self.stack.append(d)
                continue
            if op == Op.GET_INDEX:
                idx = self.stack.pop()
                target = self.stack.pop()
                if isinstance(target, list):
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        raise InterpreterError(
                            "list indices must be integers"
                        )
                    n = len(target)
                    real = idx + n if idx < 0 else idx
                    if real < 0 or real >= n:
                        raise InterpreterError(
                            f"list index out of range (index {idx}, length {n})"
                        )
                    self.stack.append(target[real])
                elif isinstance(target, dict):
                    if idx not in target:
                        raise InterpreterError(
                            f"dict key not found: {idx!r}"
                        )
                    self.stack.append(target[idx])
                elif isinstance(target, str):
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        raise InterpreterError(
                            "string indices must be integers"
                        )
                    n = len(target)
                    real = idx + n if idx < 0 else idx
                    if real < 0 or real >= n:
                        raise InterpreterError(
                            f"string index out of range"
                        )
                    self.stack.append(target[real])
                else:
                    raise InterpreterError(
                        f"cannot index {type(target).__name__}"
                    )
                continue
            if op == Op.SET_INDEX:
                val = self.stack.pop()
                idx = self.stack.pop()
                target = self.stack.pop()
                if isinstance(target, list):
                    if not isinstance(idx, int) or isinstance(idx, bool):
                        raise InterpreterError(
                            "list indices must be integers"
                        )
                    n = len(target)
                    real = idx + n if idx < 0 else idx
                    if real < 0 or real >= n:
                        raise InterpreterError(
                            f"list index out of range (index {idx}, length {n})"
                        )
                    target[real] = val
                elif isinstance(target, dict):
                    target[idx] = val
                else:
                    raise InterpreterError(
                        f"cannot index-assign {type(target).__name__}"
                    )
                continue
            if op == Op.RETURN:
                return
            raise InterpreterError(f"unknown opcode {int(op)}")


__all__ = ["VM"]
