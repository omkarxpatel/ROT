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


# ─── while + break + continue (v2.27.3) ──────────────────────────


def test_vm_while_counts_to_three():
    vm = _run("i = 0\nwhile (i < 3) { i = i + 1 }")
    assert vm.env["i"] == 3


def test_vm_while_false_skips_body():
    vm = _run("i = 0\nwhile (false) { i = i + 1 }")
    assert vm.env["i"] == 0


def test_vm_break_exits_loop():
    src = (
        "i = 0\n"
        "while (true) {\n"
        "  i = i + 1\n"
        "  if (i == 5) { break }\n"
        "}\n"
    )
    vm = _run(src)
    assert vm.env["i"] == 5


def test_vm_continue_skips_rest_of_iteration():
    src = (
        "i = 0\n"
        "sum = 0\n"
        "while (i < 5) {\n"
        "  i = i + 1\n"
        "  if (i == 3) { continue }\n"
        "  sum = sum + i\n"
        "}\n"
    )
    # 1 + 2 + 4 + 5 = 12 (skipped 3)
    vm = _run(src)
    assert vm.env["sum"] == 12


# ─── and / or short-circuit (v2.27.3) ────────────────────────────


def test_vm_and_returns_left_when_falsy():
    # `false and X` returns false without evaluating X.
    vm = _run("x = false and true")
    assert vm.env["x"] is False


def test_vm_and_returns_right_when_left_truthy():
    vm = _run("x = true and 42")
    assert vm.env["x"] == 42


def test_vm_or_returns_left_when_truthy():
    vm = _run("x = 7 or 99")
    assert vm.env["x"] == 7


def test_vm_or_returns_right_when_left_falsy():
    vm = _run('x = "" or "fallback"')
    assert vm.env["x"] == "fallback"


def test_vm_and_short_circuits_evaluating_right():
    # If short-circuit didn't work, `nope` would raise undefined-name.
    vm = _run("x = false and nope")
    assert vm.env["x"] is False


def test_vm_or_short_circuits_evaluating_right():
    vm = _run("x = true or nope")
    assert vm.env["x"] is True


# ─── Collections (v2.27.7) ───────────────────────────────────────


def test_vm_builds_empty_list_and_dict():
    vm = _run("xs = []\nd = {}")
    assert vm.env == {"xs": [], "d": {}}


def test_vm_list_literal_preserves_order():
    vm = _run("xs = [10 | 20 | 30]")
    assert vm.env["xs"] == [10, 20, 30]


def test_vm_dict_literal_preserves_key_value():
    vm = _run('d = {"a": 1 | "b": 2 | "c": 3}')
    assert vm.env["d"] == {"a": 1, "b": 2, "c": 3}


def test_vm_get_index_on_list():
    vm = _run("xs = [10 | 20 | 30]\ny = xs[1]")
    assert vm.env["y"] == 20


def test_vm_get_index_negative_wraps():
    vm = _run("xs = [10 | 20 | 30]\ny = xs[-1]")
    assert vm.env["y"] == 30


def test_vm_get_index_on_dict():
    vm = _run('d = {"a": 1 | "b": 2}\ny = d["b"]')
    assert vm.env["y"] == 2


def test_vm_get_index_on_string():
    vm = _run('s = "hello"\nc = s[1]')
    assert vm.env["c"] == "e"


def test_vm_index_out_of_range_raises():
    with pytest.raises(InterpreterError) as ei:
        _run("xs = [1 | 2]\ny = xs[5]")
    assert "out of range" in str(ei.value)


def test_vm_missing_dict_key_raises():
    with pytest.raises(InterpreterError) as ei:
        _run('d = {"a": 1}\ny = d["missing"]')
    assert "missing" in str(ei.value)


def test_vm_set_index_on_list_mutates():
    vm = _run("xs = [1 | 2 | 3]\nxs[1] = 99")
    assert vm.env["xs"] == [1, 99, 3]


def test_vm_set_index_on_dict_inserts_or_updates():
    vm = _run('d = {"a": 1}\nd["b"] = 2\nd["a"] = 99')
    assert vm.env["d"] == {"a": 99, "b": 2}


def test_vm_set_index_negative_wraps():
    vm = _run("xs = [1 | 2 | 3]\nxs[-1] = 99")
    assert vm.env["xs"] == [1, 2, 99]


def test_vm_set_index_out_of_range_raises():
    with pytest.raises(InterpreterError):
        _run("xs = [1 | 2]\nxs[5] = 9")


def test_vm_nested_list_indexing():
    vm = _run("g = [[1 | 2] | [3 | 4]]\ny = g[1][0]")
    assert vm.env["y"] == 3


# ─── For loops (v2.27.8) ─────────────────────────────────────────


def test_vm_for_loop_iterates_list():
    vm = _run("total = 0\nfor x in [1 | 2 | 3] { total = total + x }")
    assert vm.env["total"] == 6


def test_vm_for_loop_binds_var_to_each_element():
    vm = _run("last = 0\nfor n in [10 | 20 | 30 | 40] { last = n }")
    assert vm.env["last"] == 40


def test_vm_for_loop_over_empty_list_skips_body():
    vm = _run("ran = false\nfor x in [] { ran = true }")
    assert vm.env["ran"] is False


def test_vm_for_loop_over_string_iterates_chars():
    vm = _run('out = ""\nfor c in "abc" { out = out + c }')
    assert vm.env["out"] == "abc"


def test_vm_for_loop_over_dict_iterates_keys():
    # `for k in dict` iterates keys (Python semantics). Hard to
    # collect them in the VM without `append` builtin yet, so just
    # count them.
    src = (
        'd = {"a": 1 | "b": 2}\n'
        "count = 0\n"
        "for k in d {\n"
        "  count = count + 1\n"
        "}\n"
    )
    vm = _run(src)
    assert vm.env["count"] == 2


def test_vm_for_loop_break_exits_early():
    src = (
        "found = -1\n"
        "for x in [1 | 2 | 3 | 4 | 5] {\n"
        "  if (x == 3) {\n"
        "    found = x\n"
        "    break\n"
        "  }\n"
        "}\n"
    )
    vm = _run(src)
    assert vm.env["found"] == 3


def test_vm_for_loop_continue_skips_iteration():
    src = (
        "kept = 0\n"
        "for x in [1 | 2 | 3 | 4 | 5] {\n"
        "  if (x == 3) { continue }\n"
        "  kept = kept + x\n"
        "}\n"
    )
    vm = _run(src)
    # 1 + 2 + 4 + 5 = 12
    assert vm.env["kept"] == 12


def test_vm_for_loop_over_non_iterable_raises():
    with pytest.raises(InterpreterError) as ei:
        _run("for x in 42 { y = x }")
    assert "iterate" in str(ei.value)


def test_vm_nested_for_loops():
    src = (
        "total = 0\n"
        "for i in [1 | 2] {\n"
        "  for j in [10 | 20 | 30] {\n"
        "    total = total + i * j\n"
        "  }\n"
        "}\n"
    )
    # i=1: 10 + 20 + 30 = 60
    # i=2: 20 + 40 + 60 = 120
    # total = 180
    vm = _run(src)
    assert vm.env["total"] == 180


# ─── Function calls (v2.27.9) ────────────────────────────────────


def test_vm_simple_function_call_returns_value():
    src = (
        "funct add(a | b) {\n"
        "  return a + b\n"
        "}\n"
        "x = add(2 | 3)\n"
    )
    vm = _run(src)
    assert vm.env["x"] == 5


def test_vm_function_with_no_args():
    src = "funct answer() {\n  return 42\n}\nv = answer()\n"
    vm = _run(src)
    assert vm.env["v"] == 42


def test_vm_function_without_explicit_return_yields_null():
    src = "funct noop() {\n  x = 1\n}\nresult = noop()\n"
    vm = _run(src)
    assert vm.env["result"] is None


def test_vm_recursion_factorial():
    src = (
        "funct fac(n) {\n"
        "  if (n <= 1) { return 1 }\n"
        "  return n * fac(n - 1)\n"
        "}\n"
        "r = fac(5)\n"
    )
    vm = _run(src)
    assert vm.env["r"] == 120


def test_vm_function_calls_other_function():
    src = (
        "funct double(x) { return x * 2 }\n"
        "funct quad(x) { return double(double(x)) }\n"
        "v = quad(3)\n"
    )
    vm = _run(src)
    assert vm.env["v"] == 12


def test_vm_function_locals_dont_leak_to_globals():
    src = (
        "funct foo() {\n"
        "  local = 99\n"
        "  return local\n"
        "}\n"
        "out = foo()\n"
    )
    vm = _run(src)
    assert vm.env["out"] == 99
    # `local` was defined inside the function only — global env
    # should NOT carry it.
    assert "local" not in vm.env


def test_vm_function_can_read_globals():
    src = (
        "k = 10\n"
        "funct add_k(x) { return x + k }\n"
        "v = add_k(5)\n"
    )
    vm = _run(src)
    assert vm.env["v"] == 15


def test_vm_wrong_arg_count_raises():
    src = "funct one(a) { return a }\nx = one(1 | 2)\n"
    with pytest.raises(InterpreterError) as ei:
        _run(src)
    assert "argument" in str(ei.value)


def test_vm_calling_non_function_raises():
    with pytest.raises(InterpreterError) as ei:
        _run("x = 5\ny = x(1)")
    assert "cannot call" in str(ei.value)


def test_vm_function_value_renders_via_stringify():
    # `<funct foo>` matches the tree-walker's repr — important for
    # cross-engine parity once cout exists in the VM.
    src = "funct foo() {}\nf = foo\n"
    vm = _run(src)
    from rot.codegen import RotFunctionValue
    assert isinstance(vm.env["f"], RotFunctionValue)
    assert repr(vm.env["f"]) == "<funct foo>"


# ─── Builtins + CLI integration (v2.27.12) ───────────────────────


def test_vm_can_call_python_builtin_callable(capsys):
    # Pre-load the VM with cout/coutln and verify a print actually
    # reaches stdout via the CALL → Python-callable path.
    from rot.codegen import Compiler as VMCompiler
    from rot.interpreter import _builtin_cout, _builtin_coutln
    from rot.vm import VM as VMClass
    chunk = VMCompiler().compile(
        Parser(Lexer().tokenize('coutln("hi from vm")')).parse()
    )
    vm = VMClass(chunk, builtins={"coutln": _builtin_coutln, "cout": _builtin_cout})
    vm.run()
    captured = capsys.readouterr()
    assert captured.out == "hi from vm\n"


def test_vm_builtin_with_args_returns_value():
    from rot.codegen import Compiler as VMCompiler
    from rot.builtins import BUILTINS
    from rot.vm import VM as VMClass
    chunk = VMCompiler().compile(
        Parser(Lexer().tokenize('n = len([1 | 2 | 3])')).parse()
    )
    vm = VMClass(chunk, builtins=dict(BUILTINS))
    vm.run()
    assert vm.env["n"] == 3


def test_vm_cli_vm_flag_runs_program(tmp_path, capsys):
    # Smoke-test the `--vm` CLI by invoking the same entry point.
    import sys
    from rot.cli import main
    f = tmp_path / "p.rot"
    f.write_text("x = 7\ncoutln(x + 3)\n")
    argv_prior = sys.argv
    sys.argv = ["rot", "--vm", str(f)]
    try:
        main()
    finally:
        sys.argv = argv_prior
    captured = capsys.readouterr()
    assert captured.out == "10\n"
