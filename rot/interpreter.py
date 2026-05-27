"""Tree-walking interpreter — executes an `ast.Program` directly.

This is the v2.0.0 cut: `exec()` is gone. The interpreter walks the AST,
maintains a lexically-scoped environment, and runs the program's
semantics without producing Python source.

`cout` and `coutln` are bound in the global environment as Python
callables — they're the language's only built-ins so far.
"""

from __future__ import annotations

import os
from typing import Any, Callable

from . import ast
from .builtins import BUILTINS
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


class _ThrowSignal(BaseException):
    """User-raised exception value (via the `throw` statement). Caught by
    `try { ... } catch (e) { ... }`."""

    def __init__(self, value: "Any") -> None:
        self.value = value


from .builtins import _stringify


def _plus(a: Any, b: Any) -> Any:
    """`+` with string coercion: if either side is a string, both become
    strings and concatenate. Otherwise, regular numeric addition."""
    if isinstance(a, str) or isinstance(b, str):
        return _stringify(a) + _stringify(b)
    return a + b


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


class Environment:
    """A lexically-scoped variable binding map.

    `set(name, value)` walks the parent chain — if `name` is already
    bound anywhere up the chain, the existing binding is mutated.
    Otherwise a new binding is created in the current scope.

    This means closures can mutate enclosing-scope variables (the
    common `counter` idiom works), at the cost of being unable to
    deliberately shadow an outer variable by re-using its name. Use a
    different name to shadow, or a function parameter (params are
    bound directly via `set_local`, bypassing the chain walk).

    A `frozen=True` env rejects every write — used for the builtin
    layer at the root of the env chain. The user's global scope is a
    fresh child of that layer, so user `Assign` can still create new
    globals; only writes that would target a builtin (via the chain
    walk hitting the frozen layer) are rejected.
    """

    def __init__(self, parent: "Environment | None" = None, frozen: bool = False) -> None:
        self.values: dict[str, Any] = {}
        self.parent = parent
        self.frozen = frozen

    def get(self, name: str) -> Any:
        if name in self.values:
            return self.values[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise InterpreterError(f"name {name!r} is not defined")

    def set(self, name: str, value: Any) -> None:
        env: "Environment | None" = self
        while env is not None:
            if name in env.values:
                if env.frozen:
                    raise InterpreterError(
                        f"cannot reassign builtin {name!r}"
                    )
                env.values[name] = value
                return
            env = env.parent
        # Not found anywhere — declare in current scope. (The current scope
        # is never the frozen builtins layer in practice: the interpreter
        # constructs a fresh child env as the user global.)
        if self.frozen:
            raise InterpreterError(
                f"cannot define {name!r} in the builtins layer"
            )
        self.values[name] = value

    def set_local(self, name: str, value: Any) -> None:
        """Bind in THIS scope, never walking the chain. Used for function
        parameters and for `this` in methods — these must always be local
        even if the same name exists in an outer scope."""
        if self.frozen:
            raise InterpreterError(
                f"cannot reassign builtin {name!r}"
            )
        self.values[name] = value

    def _populate_frozen(self, name: str, value: Any) -> None:
        """Bypass the frozen check — only the interpreter's own
        initialization code populates the builtins layer."""
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
            local.set_local(param, value)

        prior = interpreter.env
        # `_loop_depth` is interpreter-global. Without resetting it, a `break`
        # inside this function would see a non-zero depth (because the caller
        # is in a loop) and escape into that caller's loop. Save/restore so
        # only loops lexically inside this function count.
        prior_loop_depth = interpreter._loop_depth
        interpreter._loop_depth = 0
        interpreter.env = local
        interpreter._function_depth += 1
        try:
            try:
                interpreter._execute_block(self.decl.body)
            except _ReturnSignal as signal:
                return signal.value
            except _BreakSignal:
                # A `break` that reached here was never caught by a loop
                # inside this function — it's a `break` outside of any loop
                # from the function's lexical perspective.
                raise InterpreterError("`break` outside of a loop")
            except _ContinueSignal:
                raise InterpreterError("`continue` outside of a loop")
        finally:
            interpreter.env = prior
            interpreter._function_depth -= 1
            interpreter._loop_depth = prior_loop_depth
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
        # set_local (not set) so `this` and params can't clobber outer-scope
        # variables of the same name via the chain-walk in set().
        local.set_local("this", self.instance)
        for param, value in zip(self.decl.params, args):
            local.set_local(param, value)
        prior = interpreter.env
        # See RotFunction.call: reset `_loop_depth` so loops outside this
        # method can't be broken from inside it.
        prior_loop_depth = interpreter._loop_depth
        interpreter._loop_depth = 0
        interpreter.env = local
        interpreter._function_depth += 1
        try:
            try:
                interpreter._execute_block(self.decl.body)
            except _ReturnSignal as signal:
                return signal.value
            except _BreakSignal:
                raise InterpreterError("`break` outside of a loop")
            except _ContinueSignal:
                raise InterpreterError("`continue` outside of a loop")
        finally:
            interpreter.env = prior
            interpreter._function_depth -= 1
            interpreter._loop_depth = prior_loop_depth
        return None


class Interpreter:
    def __init__(self) -> None:
        # Two-layer env: an immutable builtins layer at the root, and a
        # fresh user global as its child. Writes that walk the chain into
        # the builtins layer (e.g. `pi = 3.0`, `cout = "x"`) are rejected;
        # writes that don't (e.g. `x = 1` where `x` isn't a builtin) land
        # in the user global as usual.
        builtins_env = Environment(frozen=True)
        # `cout` / `coutln` stay defined locally because they use the
        # interpreter-internal _stringify (matters for rot-style null/true/false).
        builtins_env._populate_frozen("cout", _builtin_cout)
        builtins_env._populate_frozen("coutln", _builtin_coutln)
        # Everything else lives in rot/builtins.py.
        for name, fn in BUILTINS.items():
            builtins_env._populate_frozen(name, fn)
        self._builtins_env = builtins_env
        self.env = Environment(parent=builtins_env)
        # Module-system state.
        self._loaded_modules: set[str] = set()
        self._source_dir: "str | None" = None
        # Context tracking — used so `break`/`continue`/`return` at top level
        # raise a clear InterpreterError instead of escaping as BaseException.
        self._loop_depth: int = 0
        self._function_depth: int = 0

    def set_source_dir(self, source_dir: "str | None") -> None:
        """Tell the interpreter where the current source file lives so
        `import "rel/path"` can resolve relative to it."""
        self._source_dir = source_dir

    def execute(self, program: ast.Program) -> None:
        try:
            for stmt in program.body:
                self._execute_statement(stmt)
        except _ThrowSignal as t:
            # An uncaught `throw` at top level (or anywhere not surrounded
            # by `try`/`catch`) would otherwise escape as a raw Python
            # BaseException with a Python traceback. Convert to a clean
            # rot-side InterpreterError so the CLI prints a normal error.
            raise InterpreterError(f"uncaught throw: {_stringify(t.value)}")

    def _execute_statement(self, stmt: ast.Statement) -> None:
        if isinstance(stmt, ast.ExprStmt):
            self._evaluate(stmt.expr)
            return
        if isinstance(stmt, ast.FuncDef):
            # A `funct f` declaration ALWAYS introduces a fresh local binding,
            # never walking the parent chain. Otherwise nested `funct f` inside
            # `funct outer` would silently overwrite the outer `f` via the
            # closure-mutating `set` — a footgun. Only user `Assign` walks.
            self.env.set_local(stmt.name, RotFunction(stmt, self.env))
            return
        if isinstance(stmt, ast.ClassDef):
            # Same reasoning as FuncDef: a `class A` declaration is a fresh
            # local binding, not a rebind of any outer `A`. Otherwise nested
            # `class A` inside `funct outer` would silently overwrite the
            # outer `A` via the chain-walking `set`.
            method_map = {m.name: m for m in stmt.methods}
            self.env.set_local(stmt.name, RotClass(stmt.name, method_map, self.env))
            return
        if isinstance(stmt, ast.IfStmt):
            self._execute_if(stmt)
            return
        if isinstance(stmt, ast.Assign):
            # `this = ...` inside a method would silently mutate the local
            # `this` binding (since methods set_local "this"), breaking the
            # method body's view of its instance. Reject if `this` is in
            # scope (we're inside a method). At top level `this` isn't bound,
            # so `this = ...` there is treated as a normal name binding.
            if stmt.name == "this" and self._is_this_in_scope():
                raise InterpreterError("cannot reassign 'this'")
            new_value = self._evaluate(stmt.value)
            if stmt.op == "=":
                self.env.set(stmt.name, new_value)
            else:
                current = self.env.get(stmt.name)
                op_fn = _BINARY_OPS.get(stmt.op)
                if op_fn is None:
                    raise InterpreterError(f"unknown compound op {stmt.op!r}")
                # The plain binary-op path (_evaluate) wraps Python errors;
                # the compound-assign path must do the same so `x /= 0`,
                # `s -= 1`, `null += 1`, etc. raise InterpreterError instead
                # of leaking raw Python ZeroDivisionError/TypeError. Match
                # the style/message used in _evaluate's BinaryOp wrapper.
                try:
                    result = op_fn(current, new_value)
                except ZeroDivisionError:
                    raise InterpreterError("division by zero")
                except TypeError as e:
                    raise InterpreterError(
                        f"cannot apply {stmt.op!r} to {type(current).__name__} "
                        f"and {type(new_value).__name__}: {e}"
                    )
                self.env.set(stmt.name, result)
            return
        if isinstance(stmt, ast.LetStmt):
            # `let x = ...` introduces a FRESH local binding without walking
            # the chain. The opt-in way to shadow an outer name. Shadowing a
            # builtin is allowed since the new binding lives in the current
            # scope and the chain is never walked.
            if stmt.name == "this":
                raise InterpreterError("cannot use `let` to bind 'this'")
            value = self._evaluate(stmt.value)
            self.env.set_local(stmt.name, value)
            return
        if isinstance(stmt, ast.Return):
            if self._function_depth == 0:
                raise InterpreterError("`return` outside of a function")
            value = self._evaluate(stmt.value) if stmt.value is not None else None
            raise _ReturnSignal(value)
        if isinstance(stmt, ast.WhileStmt):
            self._loop_depth += 1
            try:
                while self._evaluate(stmt.cond):
                    try:
                        self._execute_block(stmt.body)
                    except _ContinueSignal:
                        continue
                    except _BreakSignal:
                        break
            finally:
                self._loop_depth -= 1
            return
        if isinstance(stmt, ast.ForStmt):
            iterable = self._evaluate(stmt.iter)
            try:
                iterator = iter(iterable)
            except TypeError:
                raise InterpreterError(
                    f"cannot iterate over {type(iterable).__name__}"
                )
            self._loop_depth += 1
            try:
                for item in iterator:
                    # for-loop var binds at the current scope, not walking up
                    self.env.set_local(stmt.var, item)
                    try:
                        self._execute_block(stmt.body)
                    except _ContinueSignal:
                        continue
                    except _BreakSignal:
                        break
            finally:
                self._loop_depth -= 1
            return
        if isinstance(stmt, ast.BreakStmt):
            if self._loop_depth == 0:
                raise InterpreterError("`break` outside of a loop")
            raise _BreakSignal()
        if isinstance(stmt, ast.ContinueStmt):
            if self._loop_depth == 0:
                raise InterpreterError("`continue` outside of a loop")
            raise _ContinueSignal()
        if isinstance(stmt, ast.ThrowStmt):
            value = self._evaluate(stmt.value)
            raise _ThrowSignal(value)
        if isinstance(stmt, ast.ImportStmt):
            self._import_file(stmt.path)
            return
        if isinstance(stmt, ast.TryCatch):
            try:
                self._execute_block(stmt.try_block)
            except _ThrowSignal as signal:
                self._execute_catch(stmt, signal.value)
            except Exception as e:
                # Captures InterpreterError, ZeroDivisionError, KeyError, etc.
                # Control-flow signals (_Return / _Break / _Continue / _Throw)
                # subclass BaseException, so they aren't caught here.
                self._execute_catch(stmt, str(e))
            return
        if isinstance(stmt, ast.IndexAssign):
            target = self._evaluate(stmt.target)
            index = self._evaluate(stmt.index)
            new_value = self._evaluate(stmt.value)
            if stmt.op == "=":
                try:
                    target[index] = new_value
                except (IndexError, KeyError, TypeError) as e:
                    raise InterpreterError(f"index error: {e}")
            else:
                op_fn = _BINARY_OPS.get(stmt.op)
                if op_fn is None:
                    raise InterpreterError(f"unknown compound op {stmt.op!r}")
                # Read side: wrap index errors the same way the plain `=`
                # path does.
                try:
                    current = target[index]
                except (IndexError, KeyError, TypeError) as e:
                    raise InterpreterError(f"index error: {e}")
                # Op side: `xs[0] /= 0` / `xs[0] -= "a"` used to leak raw
                # Python ZeroDivisionError / TypeError. Wrap to match the
                # compound-Assign path and _evaluate's BinaryOp wrapper.
                try:
                    new_combined = op_fn(current, new_value)
                except ZeroDivisionError:
                    raise InterpreterError("division by zero")
                except TypeError as e:
                    raise InterpreterError(
                        f"cannot apply {stmt.op!r} to {type(current).__name__} "
                        f"and {type(new_value).__name__}: {e}"
                    )
                # Write side: still wrap index errors on assignment.
                try:
                    target[index] = new_combined
                except (IndexError, KeyError, TypeError) as e:
                    raise InterpreterError(f"index error: {e}")
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

    def _is_this_in_scope(self) -> bool:
        """True iff `this` is bound somewhere up the env chain. Used to
        differentiate `this = ...` inside a method (must be rejected — would
        silently mutate the local `this`) from `this = ...` at top level
        (treated as a normal name, since the user's scaffolding code may use
        it that way and `this` is not a reserved binding outside methods)."""
        env: "Environment | None" = self.env
        while env is not None:
            if "this" in env.values:
                return True
            env = env.parent
        return False

    def _execute_catch(self, stmt: ast.TryCatch, value: Any) -> None:
        """Run the catch block in a fresh local scope so the catch variable
        doesn't leak into the enclosing scope and doesn't clobber an existing
        outer binding (e.g. the math constant `e` after `catch (e)`).
        The new env's parent is the current env, so the catch body can still
        read and chain-walk-mutate enclosing names."""
        catch_env = Environment(parent=self.env)
        catch_env.set_local(stmt.catch_var, value)
        prior = self.env
        self.env = catch_env
        try:
            self._execute_block(stmt.catch_block)
        finally:
            self.env = prior

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
            try:
                return op(left, right)
            except ZeroDivisionError:
                raise InterpreterError("division by zero")
            except TypeError as e:
                raise InterpreterError(
                    f"cannot apply {expr.op!r} to {type(left).__name__} "
                    f"and {type(right).__name__}: {e}"
                )
        raise InterpreterError(f"cannot evaluate {type(expr).__name__}")

    def _evaluate_unary(self, expr: ast.UnaryOp) -> Any:
        operand = self._evaluate(expr.operand)
        if expr.op == "-":
            try:
                return -operand
            except TypeError:
                raise InterpreterError(
                    f"cannot negate {type(operand).__name__}"
                )
        if expr.op == "not":
            return not operand
        raise InterpreterError(f"unknown unary operator {expr.op!r}")

    def _evaluate_call(self, expr: ast.Call) -> Any:
        callee = self._evaluate(expr.callee)
        args = [self._evaluate(a) for a in expr.args]
        if isinstance(callee, (RotFunction, RotClass, BoundMethod)):
            try:
                return callee.call(args, self)
            except RecursionError:
                # Convert Python's recursion-depth-exceeded into a clean
                # rot-side error. Caught here (the outermost rot frame on
                # the Python stack) so it doesn't unwind further as a raw
                # Python exception.
                raise InterpreterError("call stack too deep")
        if not callable(callee):
            raise InterpreterError(f"not callable: {callee!r}")
        try:
            return callee(*args)
        except InterpreterError:
            # already in rot form — leave it alone
            raise
        except RecursionError:
            raise InterpreterError("call stack too deep")
        except (
            TypeError,
            ValueError,
            ZeroDivisionError,
            UnicodeDecodeError,
            UnicodeEncodeError,
            OSError,
        ) as e:
            name = getattr(callee, "__name__", repr(callee))
            # strip the leading underscore from internal builtin names
            # (`_builtin_input`, `_num`, `_stringify`, ...).
            display = name.lstrip("_")
            raise InterpreterError(f"{display}: {e}")


def _builtin_cout(*args: Any) -> None:
    print(*(_stringify(a) for a in args), sep="", end="")


def _builtin_coutln(*args: Any) -> None:
    print(*(_stringify(a) for a in args), sep="")


# Module-loading helpers attached as Interpreter methods below.

def _resolve_import_path(self: "Interpreter", path: str) -> str:
    if not path.endswith(".rot"):
        path = path + ".rot"
    if os.path.isabs(path):
        return os.path.abspath(path)
    base = self._source_dir if self._source_dir else os.getcwd()
    return os.path.abspath(os.path.join(base, path))


def _import_file(self: "Interpreter", path: str) -> None:
    abs_path = _resolve_import_path(self, path)
    if abs_path in self._loaded_modules:
        return  # cache: a file imports at most once per interpreter
    self._loaded_modules.add(abs_path)

    if not os.path.exists(abs_path):
        raise InterpreterError(f"cannot find module {path!r}")

    try:
        with open(abs_path, encoding="utf-8") as f:
            source = f.read()
    except PermissionError:
        raise InterpreterError(f"import {path!r}: permission denied")
    except IsADirectoryError:
        raise InterpreterError(f"import {path!r}: is a directory")
    except UnicodeDecodeError as e:
        raise InterpreterError(
            f"import {path!r}: not valid UTF-8: {e.reason}"
        )
    except OSError as e:
        raise InterpreterError(f"import {path!r}: {e}")

    # Lazy imports break the lexer/syntax → interpreter → builtins cycle.
    from .lexer import Lexer
    from .syntax import Parser

    tokens = Lexer().tokenize(source)
    program = Parser(tokens).parse()

    # Switch source dir so relative imports inside the imported file
    # resolve against ITS directory.
    prior_dir = self._source_dir
    self._source_dir = os.path.dirname(abs_path)
    try:
        self.execute(program)
    finally:
        self._source_dir = prior_dir


Interpreter._import_file = _import_file  # type: ignore[attr-defined]
