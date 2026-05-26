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


class _ReturnSignal(BaseException):
    """Internal control-flow signal carrying a return value.

    Subclasses `BaseException` (not `Exception`) so generic
    `except Exception` blocks don't swallow function returns.
    """

    def __init__(self, value: "Any") -> None:
        self.value = value


class _BreakSignal(BaseException):
    """Internal control-flow signal that exits the innermost loop."""
    pass


class _ContinueSignal(BaseException):
    """Internal control-flow signal that skips to the next loop iteration."""
    pass


def _plus(a: Any, b: Any) -> Any:
    """`+` with string coercion: if either side is a string, both become
    strings and concatenate. Otherwise, regular numeric addition."""
    if isinstance(a, str) or isinstance(b, str):
        return _stringify(a) + _stringify(b)
    return a + b


def _stringify(x: Any) -> str:
    """Convert a value to its rot-style string form.
    `null` -> 'null', booleans -> 'true'/'false', numbers/strings as-is."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    return str(x)


_BINARY_OPS: dict[str, Callable[[Any, Any], Any]] = {
    "+":  _plus,
    "-":  lambda a, b: a - b,
    "*":  lambda a, b: a * b,
    "/":  lambda a, b: a / b,
    "%":  lambda a, b: a % b,
    "<":  lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">":  lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
}


def _num(x: Any) -> Any:
    """Built-in `num()`: convert to int if integer-shaped, else float."""
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return x
    s = str(x)
    try:
        return int(s)
    except ValueError:
        return float(s)


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

    def call(self, args: list[Any], interpreter: "Interpreter") -> Any:
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
        except _ReturnSignal as signal:
            return signal.value
        finally:
            interpreter.env = prior
        return None  # fell off the end without `return`


class RotClass:
    """A user-defined class. Callable — invoking it constructs an instance."""

    def __init__(self, name: str, methods: dict[str, ast.FuncDef], closure: Environment) -> None:
        self.name = name
        self.methods = methods
        self.closure = closure

    def call(self, args: list[Any], interpreter: "Interpreter") -> "RotInstance":
        instance = RotInstance(self)
        init = self.methods.get("init")
        if init is not None:
            BoundMethod(instance, init, self.closure).call(args, interpreter)
        elif args:
            raise InterpreterError(
                f"class {self.name!r} has no init but was called with {len(args)} arg(s)"
            )
        return instance


class RotInstance:
    """An instance of a RotClass — fields stored in a dict, methods looked
    up on the class."""

    def __init__(self, cls: RotClass) -> None:
        self.cls = cls
        self.fields: dict[str, Any] = {}

    def get_member(self, name: str) -> Any:
        if name in self.fields:
            return self.fields[name]
        method = self.cls.methods.get(name)
        if method is not None:
            return BoundMethod(self, method, self.cls.closure)
        raise InterpreterError(f"no member {name!r} on {self.cls.name} instance")

    def set_member(self, name: str, value: Any) -> None:
        self.fields[name] = value


class BoundMethod:
    """A method already bound to an instance — `this` is the captured instance."""

    def __init__(self, instance: RotInstance, decl: ast.FuncDef, closure: Environment) -> None:
        self.instance = instance
        self.decl = decl
        self.closure = closure

    def call(self, args: list[Any], interpreter: "Interpreter") -> Any:
        if len(args) != len(self.decl.params):
            raise InterpreterError(
                f"method {self.decl.name!r} takes {len(self.decl.params)} "
                f"argument(s), got {len(args)}"
            )
        local = Environment(parent=self.closure)
        local.set("this", self.instance)
        for param, value in zip(self.decl.params, args):
            local.set(param, value)
        prior = interpreter.env
        interpreter.env = local
        try:
            interpreter._execute_block(self.decl.body)
        except _ReturnSignal as signal:
            return signal.value
        finally:
            interpreter.env = prior
        return None


class Interpreter:
    def __init__(self) -> None:
        self.env = Environment()
        self.env.set("cout", _builtin_cout)
        self.env.set("coutln", _builtin_coutln)
        # Conversion + introspection built-ins.
        self.env.set("str", str)
        self.env.set("num", _num)
        self.env.set("len", len)
        # Collection built-ins.
        self.env.set("range", _builtin_range)
        self.env.set("append", _builtin_append)
        self.env.set("pop", _builtin_pop)

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
        if isinstance(stmt, ast.ClassDef):
            method_map = {m.name: m for m in stmt.methods}
            self.env.set(stmt.name, RotClass(stmt.name, method_map, self.env))
            return
        if isinstance(stmt, ast.IfStmt):
            self._execute_if(stmt)
            return
        if isinstance(stmt, ast.Assign):
            new_value = self._evaluate(stmt.value)
            if stmt.op == "=":
                self.env.set(stmt.name, new_value)
            else:
                current = self.env.get(stmt.name)
                op_fn = _BINARY_OPS.get(stmt.op)
                if op_fn is None:
                    raise InterpreterError(f"unknown compound op {stmt.op!r}")
                self.env.set(stmt.name, op_fn(current, new_value))
            return
        if isinstance(stmt, ast.Return):
            value = self._evaluate(stmt.value) if stmt.value is not None else None
            raise _ReturnSignal(value)
        if isinstance(stmt, ast.WhileStmt):
            while self._evaluate(stmt.cond):
                try:
                    self._execute_block(stmt.body)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return
        if isinstance(stmt, ast.ForStmt):
            iterable = self._evaluate(stmt.iter)
            for item in iterable:
                self.env.set(stmt.var, item)
                try:
                    self._execute_block(stmt.body)
                except _ContinueSignal:
                    continue
                except _BreakSignal:
                    break
            return
        if isinstance(stmt, ast.BreakStmt):
            raise _BreakSignal()
        if isinstance(stmt, ast.ContinueStmt):
            raise _ContinueSignal()
        if isinstance(stmt, ast.IndexAssign):
            target = self._evaluate(stmt.target)
            index = self._evaluate(stmt.index)
            new_value = self._evaluate(stmt.value)
            if stmt.op == "=":
                target[index] = new_value
            else:
                op_fn = _BINARY_OPS.get(stmt.op)
                if op_fn is None:
                    raise InterpreterError(f"unknown compound op {stmt.op!r}")
                target[index] = op_fn(target[index], new_value)
            return
        if isinstance(stmt, ast.MemberAssign):
            target = self._evaluate(stmt.target)
            new_value = self._evaluate(stmt.value)
            # rot instances use set_member; everything else falls back to setattr.
            if isinstance(target, RotInstance):
                if stmt.op == "=":
                    target.set_member(stmt.member, new_value)
                else:
                    op_fn = _BINARY_OPS.get(stmt.op)
                    if op_fn is None:
                        raise InterpreterError(f"unknown compound op {stmt.op!r}")
                    current = target.get_member(stmt.member)
                    target.set_member(stmt.member, op_fn(current, new_value))
                return
            if stmt.op == "=":
                try:
                    setattr(target, stmt.member, new_value)
                except (AttributeError, TypeError) as e:
                    raise InterpreterError(f"cannot set member {stmt.member!r}: {e}")
            else:
                op_fn = _BINARY_OPS.get(stmt.op)
                if op_fn is None:
                    raise InterpreterError(f"unknown compound op {stmt.op!r}")
                current = getattr(target, stmt.member)
                try:
                    setattr(target, stmt.member, op_fn(current, new_value))
                except (AttributeError, TypeError) as e:
                    raise InterpreterError(f"cannot set member {stmt.member!r}: {e}")
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
        if isinstance(expr, ast.BoolLit):
            return expr.value
        if isinstance(expr, ast.NullLit):
            return None
        if isinstance(expr, ast.Identifier):
            return self.env.get(expr.name)
        if isinstance(expr, ast.Call):
            return self._evaluate_call(expr)
        if isinstance(expr, ast.UnaryOp):
            return self._evaluate_unary(expr)
        if isinstance(expr, ast.ListLit):
            return [self._evaluate(e) for e in expr.elements]
        if isinstance(expr, ast.DictLit):
            return {self._evaluate(k): self._evaluate(v) for k, v in expr.pairs}
        if isinstance(expr, ast.Index):
            target = self._evaluate(expr.target)
            index = self._evaluate(expr.index)
            try:
                return target[index]
            except (IndexError, KeyError, TypeError) as e:
                raise InterpreterError(f"index error: {e}")
        if isinstance(expr, ast.MemberAccess):
            target = self._evaluate(expr.target)
            # rot instances have their own member lookup; everything else
            # falls back to Python's getattr (strings, lists, dicts, etc.).
            if isinstance(target, RotInstance):
                return target.get_member(expr.member)
            try:
                return getattr(target, expr.member)
            except AttributeError:
                raise InterpreterError(
                    f"no member {expr.member!r} on {type(target).__name__}"
                )
        if isinstance(expr, ast.BinaryOp):
            # `and` / `or` short-circuit, so they can't go through the
            # straight-eval table — operands shouldn't always be evaluated.
            if expr.op == "and":
                left = self._evaluate(expr.left)
                return self._evaluate(expr.right) if left else left
            if expr.op == "or":
                left = self._evaluate(expr.left)
                return left if left else self._evaluate(expr.right)
            left = self._evaluate(expr.left)
            right = self._evaluate(expr.right)
            op = _BINARY_OPS.get(expr.op)
            if op is None:
                raise InterpreterError(f"unknown operator {expr.op!r}")
            return op(left, right)
        raise InterpreterError(f"cannot evaluate {type(expr).__name__}")

    def _evaluate_unary(self, expr: ast.UnaryOp) -> Any:
        operand = self._evaluate(expr.operand)
        if expr.op == "-":
            return -operand
        if expr.op == "not":
            return not operand
        raise InterpreterError(f"unknown unary operator {expr.op!r}")

    def _evaluate_call(self, expr: ast.Call) -> Any:
        callee = self._evaluate(expr.callee)
        args = [self._evaluate(a) for a in expr.args]
        if isinstance(callee, (RotFunction, RotClass, BoundMethod)):
            return callee.call(args, self)
        if callable(callee):
            return callee(*args)
        raise InterpreterError(f"not callable: {callee!r}")


def _builtin_cout(*args: Any) -> None:
    print(*(_stringify(a) for a in args), sep="", end="")


def _builtin_coutln(*args: Any) -> None:
    print(*(_stringify(a) for a in args), sep="")


def _builtin_range(*args: Any) -> list:
    """Built-in `range`: `range(n)` → 0..n-1; `range(a, b)` → a..b-1;
    `range(a, b, step)` → with step. Returns a real list so `for` can
    iterate without iterator-protocol complexity."""
    if len(args) == 1:
        return list(range(int(args[0])))
    if len(args) == 2:
        return list(range(int(args[0]), int(args[1])))
    if len(args) == 3:
        return list(range(int(args[0]), int(args[1]), int(args[2])))
    raise InterpreterError(f"range() takes 1-3 args, got {len(args)}")


def _builtin_append(lst: list, item: Any) -> None:
    if not isinstance(lst, list):
        raise InterpreterError(f"append: expected list, got {type(lst).__name__}")
    lst.append(item)


def _builtin_pop(lst: list, *rest: Any) -> Any:
    if not isinstance(lst, list):
        raise InterpreterError(f"pop: expected list, got {type(lst).__name__}")
    if rest:
        return lst.pop(int(rest[0]))
    return lst.pop()
