"""ROT standard library — built-in functions bound in the interpreter's
global environment at startup.

Anything in `BUILTINS` becomes a global identifier in every rot program.
"""

from __future__ import annotations

import math
import random
from typing import Any

from .errors import InterpreterError


# ==== Conversion ============================================================

def _stringify(x: Any) -> str:
    """rot-style string conversion: `null` instead of `None`,
    `true`/`false` instead of `True`/`False`. Used by `str()` and by
    interpreter's cout/coutln to keep output consistent with source."""
    if x is None:
        return "null"
    if isinstance(x, bool):
        return "true" if x else "false"
    return str(x)


def _num(x: Any) -> Any:
    """Convert to int if integer-shaped, else float."""
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

def _builtin_input(prompt: Any = "") -> str:
    try:
        return input(str(prompt) if prompt != "" else "")
    except EOFError:
        raise InterpreterError("input: end of input stream")


def _read_file(path: Any) -> str:
    try:
        with open(str(path)) as f:
            return f.read()
    except OSError as e:
        raise InterpreterError(f"read_file: {e}")


def _write_file(path: Any, content: Any) -> None:
    try:
        with open(str(path), "w") as f:
            f.write(str(content))
    except OSError as e:
        raise InterpreterError(f"write_file: {e}")


# ==== Collection helpers ====================================================

def _builtin_range(*args: Any) -> list:
    if len(args) == 1:
        return list(range(int(args[0])))
    if len(args) == 2:
        return list(range(int(args[0]), int(args[1])))
    if len(args) == 3:
        step = int(args[2])
        if step == 0:
            raise InterpreterError("range: step argument must not be zero")
        return list(range(int(args[0]), int(args[1]), step))
    raise InterpreterError(f"range() takes 1-3 args, got {len(args)}")


def _builtin_append(lst: list, item: Any) -> None:
    if not isinstance(lst, list):
        raise InterpreterError(f"append: expected list, got {type(lst).__name__}")
    lst.append(item)


def _builtin_pop(lst: list, *rest: Any) -> Any:
    if not isinstance(lst, list):
        raise InterpreterError(f"pop: expected list, got {type(lst).__name__}")
    try:
        if rest:
            return lst.pop(int(rest[0]))
        return lst.pop()
    except IndexError:
        raise InterpreterError("pop: cannot pop from empty list")


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

def _builtin_type(x: Any) -> str:
    """Return a rot-style type name."""
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
    # Lazy-import so this module doesn't depend on interpreter at load time.
    from .interpreter import RotFunction, RotClass, RotInstance, BoundMethod
    if isinstance(x, RotInstance):
        return x.cls.name
    if isinstance(x, (RotFunction, RotClass, BoundMethod)):
        return "function"
    return type(x).__name__


def _is_num(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def _is_str(x: Any) -> bool:
    return isinstance(x, str)


def _is_list(x: Any) -> bool:
    return isinstance(x, list)


def _is_dict(x: Any) -> bool:
    return isinstance(x, dict)


def _is_bool(x: Any) -> bool:
    return isinstance(x, bool)


def _is_null(x: Any) -> bool:
    return x is None


def _is_func(x: Any) -> bool:
    from .interpreter import RotFunction, RotClass, BoundMethod
    if isinstance(x, (RotFunction, RotClass, BoundMethod)):
        return True
    return callable(x) and not isinstance(x, type)


# ==== Random ================================================================

def _rand_int(a: Any, b: Any) -> int:
    lo, hi = int(a), int(b)
    if lo > hi:
        raise InterpreterError(f"rand_int: low ({lo}) > high ({hi})")
    return random.randint(lo, hi)


def _safe_sqrt(x: Any) -> float:
    try:
        return math.sqrt(x)
    except ValueError as e:
        raise InterpreterError(f"sqrt: {e}")


def _rand_float() -> float:
    return random.random()


# ==== Assertions ============================================================

def _assert(cond: Any, *rest: Any) -> None:
    if not cond:
        msg = str(rest[0]) if rest else "assertion failed"
        raise InterpreterError(msg)


# ==== Registry ==============================================================

BUILTINS: dict[str, Any] = {
    # Conversions
    "str": _stringify,
    "num": _num,
    "len": len,
    # I/O
    "input": _builtin_input,
    "read_file": _read_file,
    "write_file": _write_file,
    # Collections
    "range": _builtin_range,
    "append": _builtin_append,
    "pop": _builtin_pop,
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
    # Assertions
    "assert": _assert,
}
