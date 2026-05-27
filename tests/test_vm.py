"""Tests for the stack-based VM (rot/vm.py).

Runs compiled chunks end-to-end and checks the resulting env / stack
state. Each Z in the M2 line adds tests here alongside the codegen
tests.
"""

import pytest

from rot.codegen import Compiler
from rot.errors import InterpreterError
from rot.lexer import Lexer
from rot.syntax import Parser
from rot.vm import VM


def _run(source: str) -> VM:
    program = Parser(Lexer().tokenize(source)).parse()
    chunk = Compiler().compile(program)
    vm = VM(chunk)
    vm.run()
    return vm


# ─── Literals ────────────────────────────────────────────────────


def test_vm_runs_empty_program():
    vm = _run("")
    assert vm.env == {}
    assert vm.stack == []


def test_vm_assigns_number_literal():
    vm = _run("x = 5")
    assert vm.env == {"x": 5}


def test_vm_assigns_float_literal():
    vm = _run("x = 3.14")
    assert vm.env["x"] == 3.14


def test_vm_assigns_string_literal():
    vm = _run('s = "hello"')
    assert vm.env["s"] == "hello"


def test_vm_assigns_true_and_false_and_null():
    vm = _run("a = true\nb = false\nc = null")
    assert vm.env == {"a": True, "b": False, "c": None}


def test_vm_lets_a_value():
    vm = _run("let n = 9")
    assert vm.env == {"n": 9}


# ─── Arithmetic ──────────────────────────────────────────────────


def test_vm_adds_numbers():
    vm = _run("z = 1 + 2")
    assert vm.env["z"] == 3


def test_vm_subtracts():
    vm = _run("z = 10 - 4")
    assert vm.env["z"] == 6


def test_vm_multiplies():
    vm = _run("z = 6 * 7")
    assert vm.env["z"] == 42


def test_vm_divides():
    vm = _run("z = 9 / 2")
    assert vm.env["z"] == 4.5


def test_vm_modulo():
    vm = _run("z = 17 % 5")
    assert vm.env["z"] == 2


def test_vm_unary_minus():
    vm = _run("z = -7")
    assert vm.env["z"] == -7


def test_vm_string_concat_via_plus():
    vm = _run('s = "hi " + "there"')
    assert vm.env["s"] == "hi there"


def test_vm_string_coerces_number_via_plus():
    # Mirrors the tree-walker: `"x = " + 5` → `"x = 5"`.
    vm = _run('s = "x = " + 5')
    assert vm.env["s"] == "x = 5"


# ─── Variable lookups + chained assigns ──────────────────────────


def test_vm_chains_assignments_via_lookups():
    vm = _run("x = 1\ny = 2\nz = x + y")
    assert vm.env == {"x": 1, "y": 2, "z": 3}


def test_vm_undefined_name_raises_interpreter_error():
    with pytest.raises(InterpreterError) as ei:
        _run("x = nope")
    assert "nope" in str(ei.value)


def test_vm_division_by_zero_raises_interpreter_error():
    with pytest.raises(InterpreterError) as ei:
        _run("x = 1 / 0")
    assert "division by zero" in str(ei.value)


def test_vm_modulo_by_zero_raises_interpreter_error():
    with pytest.raises(InterpreterError) as ei:
        _run("x = 5 % 0")
    assert "modulo by zero" in str(ei.value)


def test_vm_stack_is_empty_after_clean_run():
    # Every ExprStmt POPs the result, every Assign STORE_NAMEs (popping).
    # End of program → stack empty. Important invariant.
    vm = _run("a = 1\nb = 2\nc = a + b\nlet d = c")
    assert vm.stack == []


# ─── Comparisons (v2.27.1) ───────────────────────────────────────


def test_vm_equality_numbers():
    vm = _run("a = 1 == 1\nb = 1 == 2")
    assert vm.env == {"a": True, "b": False}


def test_vm_inequality():
    vm = _run("a = 1 != 1\nb = 1 != 2")
    assert vm.env == {"a": False, "b": True}


def test_vm_less_than_chain():
    vm = _run("a = 1 < 2\nb = 2 < 2\nc = 3 < 2")
    assert vm.env == {"a": True, "b": False, "c": False}


def test_vm_less_equal():
    vm = _run("a = 2 <= 2\nb = 3 <= 2")
    assert vm.env == {"a": True, "b": False}


def test_vm_greater_than_and_equal():
    vm = _run("a = 3 > 2\nb = 2 > 3\nc = 2 >= 2\nd = 1 >= 2")
    assert vm.env == {"a": True, "b": False, "c": True, "d": False}


def test_vm_equality_works_across_types():
    # 1 == "1" should be False (Python ==). Mirrors the tree-walker.
    vm = _run('a = 1 == "1"\nb = "hi" == "hi"\nc = null == null')
    assert vm.env == {"a": False, "b": True, "c": True}


def test_vm_not_operator_truthiness():
    vm = _run("a = not true\nb = not false\nc = not null\nd = not 0")
    assert vm.env == {"a": False, "b": True, "c": True, "d": True}


def test_vm_not_preserves_python_truthiness_for_strings_and_lists():
    # `not ""` and `not 0` are True (falsy); `not "x"` is False.
    vm = _run('a = not ""\nb = not "x"')
    assert vm.env == {"a": True, "b": False}


# ─── if / elseif / else (v2.27.2) ────────────────────────────────


def test_vm_if_true_runs_then_block():
    vm = _run("x = 0\nif (true) { x = 1 }")
    assert vm.env["x"] == 1


def test_vm_if_false_skips_then_block():
    vm = _run("x = 0\nif (false) { x = 1 }")
    assert vm.env["x"] == 0


def test_vm_if_else_runs_else_when_false():
    vm = _run("if (false) { x = 1 } else { x = 2 }")
    assert vm.env["x"] == 2


def test_vm_if_else_skips_else_when_true():
    vm = _run("if (true) { x = 1 } else { x = 2 }")
    assert vm.env["x"] == 1


def test_vm_elif_chain_takes_matching_branch():
    src = (
        "if (false) { x = 1 }\n"
        "elseif (true) { x = 2 }\n"
        "elseif (false) { x = 3 }\n"
        "else { x = 4 }\n"
    )
    vm = _run(src)
    assert vm.env["x"] == 2


def test_vm_elif_chain_falls_through_to_else():
    src = (
        "if (false) { x = 1 }\n"
        "elseif (false) { x = 2 }\n"
        "else { x = 3 }\n"
    )
    vm = _run(src)
    assert vm.env["x"] == 3


def test_vm_condition_uses_truthiness_for_non_booleans():
    # ROT (and the VM) match Python: non-empty string truthy, 0 falsy.
    vm = _run('if ("x") { a = 1 } else { a = 2 }\n'
              'if (0) { b = 1 } else { b = 2 }')
    assert vm.env == {"a": 1, "b": 2}


def test_vm_nested_if_inside_then_block():
    src = (
        "x = 0\n"
        "if (true) {\n"
        "  if (true) {\n"
        "    x = 7\n"
        "  }\n"
        "}\n"
    )
    vm = _run(src)
    assert vm.env["x"] == 7
