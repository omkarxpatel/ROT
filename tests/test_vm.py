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
