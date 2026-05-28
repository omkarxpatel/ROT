"""Stack-based VM for executing bytecode produced by `rot.codegen`.

v2.27.9 added function-call frames. The VM keeps a single set of
"current" attributes (`self.chunk`, `self.ip`, `self.stack`,
`self.env`) for cheap dispatch — CALL pushes a snapshot of the
caller onto `self._frames` and overwrites the current attrs with the
function's; RETURN_VALUE restores from the saved snapshot.

The tree-walking interpreter remains the reference; the VM mirrors
its value semantics opcode-by-opcode.
"""

from __future__ import annotations

from typing import Any

from .codegen import (
    Chunk,
    RotBoundMethod,
    RotClassValue,
    RotFunctionValue,
    RotInstanceValue,
)
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
    """Compact ROT-style stringifier. Used by `_plus` for string
    coercion; also paths through CALL when a user prints a function
    value (later — `cout` not yet in the VM)."""
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, RotFunctionValue):
        return f"<funct {value.name}>"
    if isinstance(value, RotClassValue):
        return f"<class {value.name}>"
    if isinstance(value, RotInstanceValue):
        return f"<instance of {value.cls.name}>"
    if isinstance(value, RotBoundMethod):
        return (
            f"<bound method {value.instance.cls.name}.{value.method.name}>"
        )
    return str(value)


class VM:
    """Executes a `Chunk`.

    Attributes are intentionally flat for hot-path dispatch. The
    frame stack only matters at CALL / RETURN_VALUE boundaries, so
    we save snapshots there instead of dereferencing a Frame object
    on every opcode.
    """

    def __init__(
        self,
        chunk: Chunk,
        builtins: "dict[str, Any] | None" = None,
    ) -> None:
        self.chunk = chunk
        self.stack: list[Any] = []
        # Top-level (global) env is `self.env` while in the main
        # frame. CALL switches `self.env` to the function's local
        # env and stashes the globals reference on `self._globals`
        # so LOAD_NAME can fall back to it. RETURN_VALUE restores.
        #
        # The `builtins` dict (if provided) is merged into globals at
        # startup so the CLI's --vm path can hand the VM
        # `cout`/`coutln` and the rest of the standard library.
        # Builtins live in the same globals dict as user assignments;
        # there's no frozen layer yet (the tree-walker's freezing
        # semantics could land later).
        self.env: dict[str, Any] = dict(builtins) if builtins else {}
        self._globals: dict[str, Any] = self.env
        self.ip: int = 0
        # Saved-frame stack — each entry is a dict snapshotting the
        # caller's chunk / ip / stack / env at the moment of CALL.
        # On RETURN_VALUE we pop one of these and restore the attrs.
        self._frames: list[dict] = []

    def run(self) -> None:
        while self.ip < len(self.chunk.code):
            instr = self.chunk.code[self.ip]
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
                if name in self.env:
                    self.stack.append(self.env[name])
                elif self.env is not self._globals and name in self._globals:
                    self.stack.append(self._globals[name])
                else:
                    raise InterpreterError(f"name {name!r} is not defined")
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
            if op == Op.GET_ITER:
                target = self.stack.pop()
                try:
                    self.stack.append(iter(target))
                except TypeError:
                    raise InterpreterError(
                        f"cannot iterate over {type(target).__name__}"
                    )
                continue
            if op == Op.ITER_NEXT:
                target_ip = instr[1]
                iterator = self.stack[-1]
                try:
                    value = next(iterator)
                except StopIteration:
                    self.ip = target_ip
                    continue
                self.stack.append(value)
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
            if op == Op.GET_MEMBER:
                name = self.chunk.names[instr[1]]
                target = self.stack.pop()
                self.stack.append(self._get_member(target, name))
                continue
            if op == Op.SET_MEMBER:
                name = self.chunk.names[instr[1]]
                val = self.stack.pop()
                target = self.stack.pop()
                if not isinstance(target, RotInstanceValue):
                    raise InterpreterError(
                        f"cannot set member on {type(target).__name__}"
                    )
                target.fields[name] = val
                continue
            if op == Op.CALL:
                self._do_call(instr[1])
                continue
            if op == Op.RETURN_VALUE:
                if self._do_return_value():
                    return  # main frame returned — halt
                continue
            if op == Op.RETURN:
                return
            raise InterpreterError(f"unknown opcode {int(op)}")

    # ─── Call / return helpers ─────────────────────────────────────

    def _get_member(self, target: Any, name: str) -> Any:
        """Look up `target.name`. For instances: fields first, then
        class methods (returning a bound method). Anything else
        without a member surface raises InterpreterError."""
        if isinstance(target, RotInstanceValue):
            if name in target.fields:
                return target.fields[name]
            if name in target.cls.methods:
                return RotBoundMethod(
                    instance=target,
                    method=target.cls.methods[name],
                )
            raise InterpreterError(
                f"no member {name!r} on instance of {target.cls.name}"
            )
        if isinstance(target, RotClassValue):
            # Class-level method lookup (e.g. `MyClass.someMethod`)
            # isn't used by current ROT programs but keeps the
            # surface symmetric for future tests.
            if name in target.methods:
                return target.methods[name]
            raise InterpreterError(
                f"no member {name!r} on class {target.name}"
            )
        raise InterpreterError(
            f"cannot access {name!r} on {type(target).__name__}"
        )

    def _do_call(self, argc: int) -> None:
        """Handle the CALL opcode: pop args + function, then either
        (a) call a Python callable directly (builtins like
        `cout`, `len`, `str`, `pi`, …) and push the result, or
        (b) snapshot the caller and switch active attrs to a
        `RotFunctionValue`'s body chunk."""
        if argc > 0:
            args = self.stack[-argc:]
            del self.stack[-argc:]
        else:
            args = []
        func = self.stack.pop()

        if isinstance(func, RotFunctionValue):
            if len(args) != len(func.params):
                raise InterpreterError(
                    f"function {func.name!r} takes {len(func.params)} "
                    f"argument(s), got {len(args)}"
                )
            self._enter_function_frame(func, args, this=None)
            return

        if isinstance(func, RotClassValue):
            # Instantiate: create an empty instance, run init() if
            # present, push the instance back onto the caller's
            # stack. Init returns null (per the implicit-null-return
            # fall-through) — we discard that and substitute the
            # instance after the frame returns. Easiest path: just
            # push the instance NOW; if init runs, we let its
            # RETURN_VALUE push null onto the local frame's stack,
            # restore the saved caller stack which already has the
            # instance, and the null gets pushed on top of it. So we
            # ALSO need to drop that null. Hand-roll:
            instance = RotInstanceValue(cls=func, fields={})
            init = func.methods.get("init")
            if init is None:
                if args:
                    raise InterpreterError(
                        f"class {func.name!r} has no init() — "
                        f"called with {len(args)} argument(s)"
                    )
                self.stack.append(instance)
                return
            if len(args) != len(init.params):
                raise InterpreterError(
                    f"init() on class {func.name!r} takes "
                    f"{len(init.params)} argument(s), got {len(args)}"
                )
            # Push instance onto caller's stack so it'll be there
            # after init returns. Then enter init with this=instance.
            # init's RETURN_VALUE will append null on top — we need
            # to swap so the instance is back on top.
            self.stack.append(instance)
            self._enter_function_frame(init, args, this=instance)
            # Mark this frame so RETURN_VALUE knows to keep the
            # instance and drop the return value.
            self._frames[-1]["_init_instance"] = True
            return

        if isinstance(func, RotBoundMethod):
            method = func.method
            if len(args) != len(method.params):
                raise InterpreterError(
                    f"method {method.name!r} takes {len(method.params)} "
                    f"argument(s), got {len(args)}"
                )
            self._enter_function_frame(
                method, args, this=func.instance,
            )
            return

        if callable(func):
            # Builtins are plain Python callables. Wrap any
            # non-InterpreterError into one so the CLI's error
            # rendering treats it uniformly.
            try:
                result = func(*args)
            except InterpreterError:
                raise
            except TypeError as e:
                # Most likely a builtin arity mismatch — mirror the
                # tree-walker's surface as best we can.
                raise InterpreterError(str(e))
            except Exception as e:
                raise InterpreterError(str(e))
            self.stack.append(result)
            return

        raise InterpreterError(f"cannot call {type(func).__name__}")

    def _enter_function_frame(
        self,
        func: RotFunctionValue,
        args: list,
        this: "RotInstanceValue | None",
    ) -> None:
        """Snapshot the caller, switch active attrs to `func`'s body
        chunk + a fresh local env with parameters (and optional
        `this`) bound."""
        self._frames.append({
            "chunk": self.chunk,
            "ip": self.ip,
            "stack": self.stack,
            "env": self.env,
        })
        assert func.chunk is not None
        self.chunk = func.chunk
        self.ip = 0
        self.stack = []
        local_env: dict[str, Any] = {}
        if this is not None:
            local_env["this"] = this
        for name, val in zip(func.params, args):
            local_env[name] = val
        self.env = local_env

    def _do_return_value(self) -> bool:
        """Handle the RETURN_VALUE opcode. Returns True if the main
        frame just returned (signaling the run loop to halt)."""
        retval = self.stack.pop() if self.stack else None
        if not self._frames:
            self.stack.append(retval)
            return True
        saved = self._frames.pop()
        self.chunk = saved["chunk"]
        self.ip = saved["ip"]
        self.stack = saved["stack"]
        self.env = saved["env"]
        # Special case: returning from a class's `init` method. The
        # caller already pushed the new instance onto its stack
        # before entering init; init's return value (always null
        # from the implicit fall-through) is discarded.
        if saved.get("_init_instance"):
            return False
        self.stack.append(retval)
        return False


__all__ = ["VM"]
