"""ROT standard library — built-in functions bound in the interpreter's
global environment at startup.

Anything in `BUILTINS` becomes a global identifier in every rot program.
"""

from __future__ import annotations

import math
import random
import sys
from typing import Any

from .errors import InterpreterError


def _arity(name: str, args: tuple, expected: Any) -> None:
    """Raise an InterpreterError if `args` doesn't match `expected`.

    `expected` is either an int (exact count) or a (min, max) tuple. Using
    this from a `*args` builtin keeps the Python parameter list out of the
    error message, so users see rot-style names like `num` instead of
    internal `_num()` Python repr.
    """
    n = len(args)
    if isinstance(expected, int):
        if n != expected:
            plural = "" if expected == 1 else "s"
            raise InterpreterError(
                f"{name}: takes {expected} arg{plural}, got {n}"
            )
        return
    lo, hi = expected
    if n < lo or n > hi:
        if lo == hi:
            raise InterpreterError(
                f"{name}: takes {lo} arg(s), got {n}"
            )
        raise InterpreterError(
            f"{name}: takes {lo}-{hi} args, got {n}"
        )


# ==== Conversion ============================================================

def _stringify(x: Any, _seen: "set[int] | None" = None) -> str:
    """rot-style string conversion: `null` instead of `None`,
    `true`/`false` instead of `True`/`False`. Used by `str()` and by
    interpreter's cout/coutln to keep output consistent with source.

    Lists render with rot's `|` separator (`[a | b | c]`) and dicts render
    as `{k: v | k2: v2}` — both recurse so nested elements use rot style
    too. String keys in dicts are double-quoted (matching rot literal
    syntax); other keys are stringified recursively.

    `_seen` is an internal id() set for cycle detection — a list/dict seen
    twice on the recursion stack renders as `[...]` / `{...}` rather than
    recursing forever. (B61: Python's `str()` does this via its own
    "we've seen this id" hack, but it produces `[...]` with the wrong
    surrounding brackets when ROT output diverges from Python repr —
    this implementation owns the cycle marker itself.)
    """
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    if isinstance(x, list):
        if _seen is None:
            _seen = set()
        if id(x) in _seen:
            return "[...]"
        _seen.add(id(x))
        try:
            return "[" + " | ".join(_stringify(item, _seen) for item in x) + "]"
        finally:
            _seen.discard(id(x))
    if isinstance(x, dict):
        if _seen is None:
            _seen = set()
        if id(x) in _seen:
            return "{...}"
        _seen.add(id(x))
        try:
            return "{" + " | ".join(
                f"{_stringify_key(k, _seen)}: {_stringify(v, _seen)}"
                for k, v in x.items()
            ) + "}"
        finally:
            _seen.discard(id(x))
    # Lazy-import the interpreter types so this module doesn't depend on
    # interpreter at load time (already the pattern in _builtin_type).
    from .interpreter import RotInstance, RotFunction, RotClass, BoundMethod
    if isinstance(x, RotInstance):
        return _stringify_instance(x)
    if isinstance(x, BoundMethod):
        # Order matters: BoundMethod check before RotFunction/RotClass since
        # BoundMethod isn't a subclass of either, but keeping the most
        # specific shape first matches the renderers below.
        return f"<method {x.instance.cls.name}.{x.decl.name}>"
    if isinstance(x, RotFunction):
        return f"<funct {x.decl.name}>"
    if isinstance(x, RotClass):
        return f"<class {x.name}>"
    return str(x)


def _stringify_instance(instance: Any) -> str:
    """Render a `RotInstance` for output.

    Default form: `<instance of {ClassName}>`. If the user defined a
    `to_string()` method on the class, call it with no args and use its
    return value — gives users an override hook for instance display. If
    `to_string` raises, returns a non-string, or has the wrong arity, fall
    back to the default form silently (display must not crash output).

    Cycle protection: if `to_string()` re-enters _stringify on the same
    instance (`return str(this) + ...`), the inner call short-circuits to
    `<instance of {ClassName}>` to avoid infinite recursion. The list/dict
    cycle marker (`[...]` / `{...}`) doesn't catch this because instances
    aren't tracked in `_seen`. _ACTIVE_INSTANCE_IDS records instances
    currently being stringified, scoped via try/finally so sibling
    occurrences of the same instance still render fully.
    """
    method = instance.cls.methods.get("to_string")
    if method is not None:
        if id(instance) in _ACTIVE_INSTANCE_IDS:
            # Re-entrant `to_string()` on the same instance — break the loop.
            return f"<instance of {instance.cls.name}>"
        # Find the active Interpreter. Set at Interpreter() construction
        # time, so any cout/coutln/str/f-string path through _stringify
        # will see it. If there's no active interpreter (extremely unusual
        # — direct call from a test before any Interpreter was built), we
        # silently fall back to the default form.
        interp = _active_interpreter()
        if interp is not None:
            from .interpreter import BoundMethod
            bound = BoundMethod(instance, method, instance.cls.closure)
            _ACTIVE_INSTANCE_IDS.add(id(instance))
            try:
                result = bound.call([], interp)
                if isinstance(result, str):
                    return result
            except Exception:
                # to_string raised or had the wrong arity — fall back to
                # the default form rather than crashing the display path.
                pass
            finally:
                _ACTIVE_INSTANCE_IDS.discard(id(instance))
    return f"<instance of {instance.cls.name}>"


# Tracks instances whose `to_string()` is currently executing. Used to
# detect re-entry on the same instance (e.g. `to_string` calls `str(this)`)
# and break the loop. Cleared in try/finally so sibling renders work.
_ACTIVE_INSTANCE_IDS: "set[int]" = set()


# Tracks the currently-running Interpreter so `_stringify` can invoke
# user-defined `to_string()` methods without needing the interpreter
# passed explicitly through every `_stringify` site (cout, coutln, str,
# f-strings, assert, etc.). Set in `Interpreter.__init__` and updated as a
# stack if needed; for single-interpreter use the simple global is fine.
_ACTIVE_INTERPRETER: Any = None


def _active_interpreter() -> Any:
    return _ACTIVE_INTERPRETER


def _set_active_interpreter(interp: Any) -> None:
    global _ACTIVE_INTERPRETER
    _ACTIVE_INTERPRETER = interp


def _stringify_key(k: Any, _seen: "set[int] | None" = None) -> str:
    """Render a dict key. String keys are double-quoted so the output looks
    like a rot dict literal; everything else goes through `_stringify`."""
    if isinstance(k, str):
        return f'"{k}"'
    return _stringify(k, _seen)


def _builtin_str(*args: Any) -> str:
    _arity("str", args, 1)
    return _stringify(args[0])


def _builtin_num(*args: Any) -> Any:
    """Convert to int if integer-shaped, else float."""
    _arity("num", args, 1)
    x = args[0]
    if isinstance(x, bool):
        return int(x)
    if isinstance(x, (int, float)):
        return x
    s = str(x)
    try:
        return int(s)
    except ValueError:
        return float(s)


# ==== I/O ===================================================================

def _builtin_input(*args: Any) -> str:
    _arity("input", args, (0, 1))
    prompt = args[0] if args else ""
    try:
        return input(_stringify(prompt) if prompt != "" else "")
    except EOFError:
        raise InterpreterError("input: end of input stream")


def _read_file(*args: Any) -> str:
    _arity("read_file", args, 1)
    path = args[0]
    try:
        with open(str(path), encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError as e:
        raise InterpreterError(
            f"read_file: {path!r} is not valid UTF-8: {e.reason}"
        )
    except OSError as e:
        raise InterpreterError(f"read_file: {e}")


def _write_file(*args: Any) -> None:
    _arity("write_file", args, 2)
    path, content = args
    try:
        with open(str(path), "w", encoding="utf-8") as f:
            f.write(str(content))
    except UnicodeEncodeError as e:
        raise InterpreterError(
            f"write_file: cannot encode content as UTF-8: {e.reason}"
        )
    except OSError as e:
        raise InterpreterError(f"write_file: {e}")


# ==== Collection helpers ====================================================

def _range_int(arg: Any, position: str) -> int:
    """Validate a range positional argument is an integer.

    Bools are accepted because `isinstance(True, int)` is true in Python and
    they pass through cleanly as 0/1; floats are rejected because
    `int(0.5) == 0` silently truncates and surprised users (B28).
    """
    if not isinstance(arg, int):
        raise InterpreterError(
            f"range: {position} argument must be an integer, got "
            f"{type(arg).__name__}"
        )
    return int(arg)


def _builtin_range(*args: Any) -> list:
    if len(args) == 1:
        return list(range(_range_int(args[0], "stop")))
    if len(args) == 2:
        return list(range(
            _range_int(args[0], "start"),
            _range_int(args[1], "stop"),
        ))
    if len(args) == 3:
        start = _range_int(args[0], "start")
        stop = _range_int(args[1], "stop")
        step = _range_int(args[2], "step")
        if step == 0:
            raise InterpreterError("range: step argument must not be zero")
        return list(range(start, stop, step))
    raise InterpreterError(f"range() takes 1-3 args, got {len(args)}")


def _builtin_append(*args: Any) -> None:
    _arity("append", args, 2)
    lst, item = args
    if not isinstance(lst, list):
        raise InterpreterError(f"append: expected list, got {type(lst).__name__}")
    lst.append(item)


def _builtin_pop(*args: Any) -> Any:
    _arity("pop", args, (1, 2))
    lst = args[0]
    rest = args[1:]
    if not isinstance(lst, list):
        raise InterpreterError(f"pop: expected list, got {type(lst).__name__}")
    if not rest:
        if not lst:
            raise InterpreterError("pop: cannot pop from empty list")
        return lst.pop()
    # Indexed pop: distinguish "list is empty" from "index out of range".
    if not lst:
        raise InterpreterError("pop: cannot pop from empty list")
    idx = int(rest[0])
    if idx < -len(lst) or idx >= len(lst):
        raise InterpreterError(
            f"pop: index {idx} out of range for list of length {len(lst)}"
        )
    return lst.pop(idx)


# ==== Math ==================================================================

def _builtin_min(*args: Any) -> Any:
    if len(args) == 1 and hasattr(args[0], "__iter__") and not isinstance(args[0], str):
        return min(args[0])
    return min(args)


def _builtin_max(*args: Any) -> Any:
    if len(args) == 1 and hasattr(args[0], "__iter__") and not isinstance(args[0], str):
        return max(args[0])
    return max(args)


def _builtin_round(x: Any, *rest: Any) -> Any:
    if rest:
        return round(x, int(rest[0]))
    return round(x)


# ==== Type ==================================================================

def _builtin_type(*args: Any) -> str:
    """Return a rot-style type name."""
    _arity("type", args, 1)
    x = args[0]
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "bool"
    if isinstance(x, int):
        return "int"
    if isinstance(x, float):
        return "float"
    if isinstance(x, str):
        return "string"
    if isinstance(x, list):
        return "list"
    if isinstance(x, dict):
        return "dict"
    # I37: `d.keys()`, `d.values()`, `d.items()` return Python view objects
    # whose `type(x).__name__` is `"dict_keys"` / `"dict_values"` /
    # `"dict_items"` — Python internals leaking through `type()`. They're
    # list-like (iterable, len-able), so report as `"list"`. This mirrors
    # what users see when iterating them.
    py_type_name = type(x).__name__
    if py_type_name in ("dict_keys", "dict_values", "dict_items"):
        return "list"
    # Lazy-import so this module doesn't depend on interpreter at load time.
    from .interpreter import RotFunction, RotClass, RotInstance, BoundMethod
    if isinstance(x, RotInstance):
        # B86: returning the bare class name (`"int"`, `"list"`, etc.) for a
        # user instance could collide with a primitive type name — `class
        # int {}` followed by `type(int())` previously returned `"int"`,
        # indistinguishable from a real int. Wrap user-instance type names
        # in angle brackets so they're always visually distinct from the
        # primitive types (`int`, `float`, `string`, `list`, ...).
        return f"<{x.cls.name}>"
    if isinstance(x, (RotFunction, RotClass, BoundMethod)):
        return "function"
    return py_type_name


def _is_num(*args: Any) -> bool:
    _arity("is_num", args, 1)
    x = args[0]
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_str(*args: Any) -> bool:
    _arity("is_str", args, 1)
    return isinstance(args[0], str)


def _is_list(*args: Any) -> bool:
    _arity("is_list", args, 1)
    return isinstance(args[0], list)


def _is_dict(*args: Any) -> bool:
    _arity("is_dict", args, 1)
    return isinstance(args[0], dict)


def _is_bool(*args: Any) -> bool:
    _arity("is_bool", args, 1)
    return isinstance(args[0], bool)


def _is_null(*args: Any) -> bool:
    _arity("is_null", args, 1)
    return args[0] is None


def _is_func(*args: Any) -> bool:
    _arity("is_func", args, 1)
    x = args[0]
    from .interpreter import RotFunction, RotClass, BoundMethod
    if isinstance(x, (RotFunction, RotClass, BoundMethod)):
        return True
    return callable(x) and not isinstance(x, type)


# ==== Random ================================================================

def _rand_int(*args: Any) -> int:
    _arity("rand_int", args, 2)
    lo, hi = int(args[0]), int(args[1])
    if lo > hi:
        raise InterpreterError(f"rand_int: low ({lo}) > high ({hi})")
    return random.randint(lo, hi)


def _safe_sqrt(x: Any) -> float:
    try:
        return math.sqrt(x)
    except ValueError as e:
        raise InterpreterError(f"sqrt: {e}")


def _rand_float(*args: Any) -> float:
    _arity("rand_float", args, 0)
    return random.random()


# ==== Assertions ============================================================

def _assert(*args: Any) -> None:
    _arity("assert", args, (1, 2))
    cond = args[0]
    rest = args[1:]
    if not cond:
        msg = _stringify(rest[0]) if rest else "assertion failed"
        raise InterpreterError(msg)


# ==== v2.25.8: additional builtins ==========================================

def _builtin_sum(*args: Any) -> Any:
    """Sum a numeric list. Mirrors Python's sum(), but rejects non-numeric
    elements with a clear rot-styled error rather than the default
    TypeError ('+' between int and str)."""
    _arity("sum", args, 1)
    xs = args[0]
    if not isinstance(xs, list):
        raise InterpreterError(
            f"sum: expected list, got {type(xs).__name__}"
        )
    total: Any = 0
    for i, x in enumerate(xs):
        if not isinstance(x, (int, float)) or isinstance(x, bool):
            # Reject bools explicitly: Python's bool <: int means True/False
            # would silently coerce to 1/0 and surprise users (see B28 for
            # the same rationale on `range`).
            raise InterpreterError(
                f"sum: element {i} is {type(x).__name__}, not a number"
            )
        total += x
    return total


def _builtin_sorted(*args: Any) -> list:
    """Return a NEW sorted list (input untouched). Raises a clean error
    on mixed types or non-comparable elements rather than Python's
    `TypeError: '<' not supported between ...`."""
    _arity("sorted", args, 1)
    xs = args[0]
    if not isinstance(xs, list):
        raise InterpreterError(
            f"sorted: expected list, got {type(xs).__name__}"
        )
    try:
        return sorted(xs)
    except TypeError as e:
        raise InterpreterError(f"sorted: {e}")


def _builtin_reversed(*args: Any) -> list:
    """Return a NEW reversed list (input untouched)."""
    _arity("reversed", args, 1)
    xs = args[0]
    if not isinstance(xs, list):
        raise InterpreterError(
            f"reversed: expected list, got {type(xs).__name__}"
        )
    return list(reversed(xs))


def _builtin_keys(*args: Any) -> list:
    """Return dict keys as a real ROT list (not a Python view object).
    I37 flagged that `d.keys()` leaks a `dict_keys` view through; the
    free-function form here returns a proper list."""
    _arity("keys", args, 1)
    d = args[0]
    if not isinstance(d, dict):
        raise InterpreterError(
            f"keys: expected dict, got {type(d).__name__}"
        )
    return list(d.keys())


def _builtin_values(*args: Any) -> list:
    _arity("values", args, 1)
    d = args[0]
    if not isinstance(d, dict):
        raise InterpreterError(
            f"values: expected dict, got {type(d).__name__}"
        )
    return list(d.values())


def _builtin_items(*args: Any) -> list:
    """Return key/value pairs as a list of two-element lists. (Tuples
    aren't a ROT type, so we use nested lists.) Iterates cleanly in a
    `for kv in items(d) { ... }` loop."""
    _arity("items", args, 1)
    d = args[0]
    if not isinstance(d, dict):
        raise InterpreterError(
            f"items: expected dict, got {type(d).__name__}"
        )
    return [[k, v] for k, v in d.items()]


def _builtin_chr(*args: Any) -> str:
    """Convert a Unicode codepoint to its single-character string."""
    _arity("chr", args, 1)
    n = args[0]
    if isinstance(n, bool) or not isinstance(n, int):
        raise InterpreterError(
            f"chr: expected int, got {type(n).__name__}"
        )
    try:
        return chr(n)
    except (ValueError, OverflowError) as e:
        raise InterpreterError(f"chr: {e}")


def _builtin_ord(*args: Any) -> int:
    """Return the Unicode codepoint of a single-character string."""
    _arity("ord", args, 1)
    s = args[0]
    if not isinstance(s, str):
        raise InterpreterError(
            f"ord: expected single-character string, got {type(s).__name__}"
        )
    if len(s) != 1:
        raise InterpreterError(
            f"ord: expected single-character string, got length {len(s)}"
        )
    return ord(s)


def _builtin_seed(*args: Any) -> None:
    """Seed the RNG used by `rand_int` / `rand_float`. Deterministic
    tests can pin a seed to get reproducible random output."""
    _arity("seed", args, 1)
    n = args[0]
    if isinstance(n, bool) or not isinstance(n, int):
        raise InterpreterError(
            f"seed: expected int, got {type(n).__name__}"
        )
    random.seed(n)


def _builtin_exit(*args: Any) -> None:
    """Terminate the process with an integer exit code. `exit()` with
    no args defaults to 0. Raises Python's SystemExit; the CLI lets
    that propagate (it's BaseException, not InterpreterError) so the
    process exits cleanly with the requested code."""
    _arity("exit", args, (0, 1))
    if args:
        code = args[0]
        if isinstance(code, bool) or not isinstance(code, int):
            raise InterpreterError(
                f"exit: expected int code, got {type(code).__name__}"
            )
        sys.exit(int(code))
    sys.exit(0)


# ==== Registry ==============================================================

BUILTINS: dict[str, Any] = {
    # Conversions
    "str": _builtin_str,
    "num": _builtin_num,
    "len": len,
    "chr": _builtin_chr,
    "ord": _builtin_ord,
    # I/O
    "input": _builtin_input,
    "read_file": _read_file,
    "write_file": _write_file,
    "exit": _builtin_exit,
    # Collections
    "range": _builtin_range,
    "append": _builtin_append,
    "pop": _builtin_pop,
    "sum": _builtin_sum,
    "sorted": _builtin_sorted,
    "reversed": _builtin_reversed,
    "keys": _builtin_keys,
    "values": _builtin_values,
    "items": _builtin_items,
    # Math
    "abs": abs,
    "min": _builtin_min,
    "max": _builtin_max,
    "pow": pow,
    "sqrt": _safe_sqrt,
    "floor": math.floor,
    "ceil": math.ceil,
    "round": _builtin_round,
    "pi": math.pi,
    "e": math.e,
    # Type introspection
    "type": _builtin_type,
    "is_num": _is_num,
    "is_str": _is_str,
    "is_list": _is_list,
    "is_dict": _is_dict,
    "is_bool": _is_bool,
    "is_null": _is_null,
    "is_func": _is_func,
    # Random
    "rand_int": _rand_int,
    "rand_float": _rand_float,
    "seed": _builtin_seed,
    # Assertions
    "assert": _assert,
}
