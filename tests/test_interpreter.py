"""Tests for the tree-walking interpreter (rot/interpreter.py)."""

import contextlib
import io

import pytest

from rot import ast
from rot.errors import InterpreterError
from rot.interpreter import Interpreter
from rot.lexer import Lexer
from rot.syntax import Parser


def _run(source: str) -> str:
    program = Parser(Lexer().tokenize(source)).parse()
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        Interpreter().execute(program)
    return captured.getvalue()


def test_coutln_prints_with_trailing_newline():
    assert _run('coutln("hi")') == "hi\n"


def test_cout_prints_without_newline():
    assert _run('cout("hi")') == "hi"


def test_multiple_print_calls_are_concatenated():
    assert _run('cout("a")\ncout("b")\ncoutln("c")') == "abc\n"


def test_function_definition_and_call():
    src = 'funct greet(name) { coutln(name) }\ngreet("world")'
    assert _run(src) == "world\n"


def test_function_with_multiple_params_separated_by_pipe():
    src = 'funct add(x | y) { coutln(x + y) }\nadd(2 | 3)'
    assert _run(src) == "5\n"


def test_if_else_takes_correct_branch():
    src = (
        'funct pick(x) {\n'
        '    if (x > 0) { coutln("positive") }\n'
        '    else { coutln("non-positive") }\n'
        '}\n'
        'pick(5)'
    )
    assert _run(src) == "positive\n"


def test_if_elseif_else_full_chain():
    src = (
        'funct cmp(x | y) {\n'
        '    if (x > y) { coutln("gt") }\n'
        '    elseif (x == y) { coutln("eq") }\n'
        '    else { coutln("lt") }\n'
        '}\n'
        'cmp(1 | 1)'
    )
    assert _run(src) == "eq\n"


def test_arithmetic_precedence_matches_pratt_parser():
    # 1 + 2 * 3 should compute to 7, not 9.
    assert _run("coutln(1 + 2 * 3)") == "7\n"


def test_parenthesized_arithmetic():
    assert _run("coutln((1 + 2) * 3)") == "9\n"


def test_undefined_name_raises_interpreter_error():
    program = Parser(Lexer().tokenize("nope()")).parse()
    with pytest.raises(InterpreterError) as exc_info:
        Interpreter().execute(program)
    assert "nope" in str(exc_info.value)


def test_wrong_arity_raises_interpreter_error():
    program = Parser(Lexer().tokenize(
        'funct one(x) { coutln(x) }\none(1 | 2)'
    )).parse()
    with pytest.raises(InterpreterError) as exc_info:
        Interpreter().execute(program)
    assert "one" in str(exc_info.value)
    assert "1" in str(exc_info.value)


def test_variable_assignment_and_use():
    assert _run("x = 5\ncoutln(x)") == "5\n"


def test_assignment_reuses_existing_binding():
    src = "x = 1\nx = x + 41\ncoutln(x)"
    assert _run(src) == "42\n"


def test_function_returns_value():
    src = 'funct add(x | y) { return x + y }\ncoutln(add(2 | 3))'
    assert _run(src) == "5\n"


def test_bare_return_yields_null():
    src = 'funct nothing() { return }\ncoutln(nothing())'
    assert _run(src) == "null\n"


def test_falling_off_function_end_returns_null():
    src = 'funct silent() { x = 1 }\ncoutln(silent())'
    assert _run(src) == "null\n"


def test_early_return_short_circuits_remaining_statements():
    src = (
        'funct first_positive(x) {\n'
        '    if (x > 0) { return "yes" }\n'
        '    return "no"\n'
        '}\n'
        'coutln(first_positive(5))\n'
        'coutln(first_positive(0-1))'
    )
    # 0-1 == -1 via the arithmetic; tests both branches.
    assert _run(src) == "yes\nno\n"


def test_return_value_threads_through_call_chain():
    src = (
        'funct double(x) { return x + x }\n'
        'funct quadruple(x) { return double(double(x)) }\n'
        'coutln(quadruple(3))'
    )
    assert _run(src) == "12\n"


def test_while_loop_counts_to_three():
    src = (
        'i = 1\n'
        'while (i <= 3) {\n'
        '    coutln(i)\n'
        '    i = i + 1\n'
        '}'
    )
    assert _run(src) == "1\n2\n3\n"


def test_unary_minus_negates():
    assert _run("coutln(-5)") == "-5\n"
    assert _run("x = 7\ncoutln(-x)") == "-7\n"


def test_modulo_arithmetic():
    assert _run("coutln(10 % 3)") == "1\n"
    assert _run("coutln(15 % 5)") == "0\n"


def test_boolean_literals_print_lowercase():
    # rot uses lowercase `true`/`false` in source, so cout/coutln render the same.
    assert _run("coutln(true)") == "true\n"
    assert _run("coutln(false)") == "false\n"


def test_null_literal_prints_lowercase():
    assert _run("coutln(null)") == "null\n"


def test_and_or_short_circuit():
    # If `or` short-circuits, the right-hand `oops()` is never called.
    src = (
        'funct oops() { return 1 / 0 }\n'
        'coutln(true or oops())'
    )
    assert _run(src) == "true\n"


def test_not_inverts_truthiness():
    assert _run("coutln(not true)") == "false\n"
    assert _run("coutln(not false)") == "true\n"
    assert _run("coutln(not (1 == 1))") == "false\n"


def test_str_num_len_builtins():
    assert _run('coutln(str(42))') == "42\n"
    assert _run('coutln(num("100"))') == "100\n"
    assert _run('coutln(len("hello"))') == "5\n"


def test_float_literal_evaluates():
    assert _run("coutln(3.14)") == "3.14\n"


def test_string_concatenation_with_number_coerces():
    assert _run('coutln("count: " + 42)') == "count: 42\n"


def test_string_concatenation_with_bool_uses_rot_style():
    assert _run('coutln("flag: " + true)') == "flag: true\n"


def test_string_escapes_are_decoded():
    assert _run(r'cout("a\nb")') == "a\nb"
    assert _run(r'cout("tab\there")') == "tab\there"


def test_escaped_quote_in_string():
    assert _run(r'coutln("she said \"hi\"")') == 'she said "hi"\n'


def test_compound_assign_plus():
    assert _run("x = 5\nx += 3\ncoutln(x)") == "8\n"


def test_compound_assign_all_ops():
    assert _run("x = 10\nx -= 3\ncoutln(x)") == "7\n"
    assert _run("x = 4\nx *= 3\ncoutln(x)") == "12\n"
    assert _run("x = 10\nx /= 4\ncoutln(x)") == "2.5\n"
    assert _run("x = 10\nx %= 3\ncoutln(x)") == "1\n"


def test_compound_assign_string_concat():
    assert _run('s = "hello"\ns += " world"\ncoutln(s)') == "hello world\n"


def test_list_literal_and_indexing():
    src = 'xs = [1 | 2 | 3]\ncoutln(xs[0])\ncoutln(xs[2])'
    assert _run(src) == "1\n3\n"


def test_list_index_assign():
    src = 'xs = [1 | 2 | 3]\nxs[1] = 99\ncoutln(xs[1])'
    assert _run(src) == "99\n"


def test_list_compound_index_assign():
    src = 'xs = [10 | 20 | 30]\nxs[1] += 5\ncoutln(xs[1])'
    assert _run(src) == "25\n"


def test_for_loop_iterates_a_list():
    src = (
        'for x in [10 | 20 | 30] {\n'
        '    coutln(x)\n'
        '}'
    )
    assert _run(src) == "10\n20\n30\n"


def test_for_loop_with_range():
    src = (
        'for i in range(3) {\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "0\n1\n2\n"


def test_range_with_two_args():
    src = (
        'for i in range(2 | 5) {\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "2\n3\n4\n"


def test_break_exits_loop():
    src = (
        'for i in range(10) {\n'
        '    if (i == 3) { break }\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "0\n1\n2\n"


def test_continue_skips_iteration():
    src = (
        'for i in range(5) {\n'
        '    if (i % 2 == 0) { continue }\n'
        '    coutln(i)\n'
        '}'
    )
    assert _run(src) == "1\n3\n"


def test_break_in_while_loop():
    src = (
        'i = 0\n'
        'while (true) {\n'
        '    if (i >= 3) { break }\n'
        '    coutln(i)\n'
        '    i += 1\n'
        '}'
    )
    assert _run(src) == "0\n1\n2\n"


def test_append_and_len():
    src = (
        'xs = [1 | 2]\n'
        'append(xs | 3)\n'
        'append(xs | 4)\n'
        'coutln(len(xs))\n'
        'coutln(xs[3])'
    )
    assert _run(src) == "4\n4\n"


def test_pop_removes_and_returns_last():
    src = (
        'xs = [1 | 2 | 3]\n'
        'last = pop(xs)\n'
        'coutln(last)\n'
        'coutln(len(xs))'
    )
    assert _run(src) == "3\n2\n"


def test_nested_indexing():
    src = (
        'grid = [[1 | 2] | [3 | 4]]\n'
        'coutln(grid[0][1])\n'
        'coutln(grid[1][0])'
    )
    assert _run(src) == "2\n3\n"


def test_string_indexing_returns_char():
    assert _run('s = "hello"\ncoutln(s[1])') == "e\n"


def test_string_iteration():
    src = (
        'for ch in "abc" {\n'
        '    coutln(ch)\n'
        '}'
    )
    assert _run(src) == "a\nb\nc\n"


def test_string_method_via_member_access():
    # `.upper()` is Python's str method, exposed for free via member access.
    assert _run('coutln("hello".upper())') == "HELLO\n"


def test_list_method_via_member_access():
    src = (
        'xs = [3 | 1 | 2]\n'
        'xs.sort()\n'
        'coutln(xs[0])'
    )
    assert _run(src) == "1\n"


def test_string_split():
    src = (
        'parts = "a,b,c".split(",")\n'
        'coutln(parts[0])\n'
        'coutln(parts[2])'
    )
    assert _run(src) == "a\nc\n"


def test_empty_dict_literal():
    src = "d = {}\ncoutln(len(d))"
    assert _run(src) == "0\n"


def test_dict_literal_and_access():
    src = (
        'd = {"name": "alice" | "age": 30}\n'
        'coutln(d["name"])\n'
        'coutln(d["age"])'
    )
    assert _run(src) == "alice\n30\n"


def test_dict_assignment_creates_key():
    src = (
        'd = {}\n'
        'd["score"] = 100\n'
        'coutln(d["score"])'
    )
    assert _run(src) == "100\n"


def test_dict_iteration_yields_keys():
    src = (
        'd = {"a": 1 | "b": 2}\n'
        'count = 0\n'
        'for k in d {\n'
        '    count += 1\n'
        '}\n'
        'coutln(count)'
    )
    assert _run(src) == "2\n"


def test_dict_methods_via_member_access():
    # Python's dict.keys() returns a view; len works on it.
    src = (
        'd = {"a": 1 | "b": 2 | "c": 3}\n'
        'coutln(len(d.keys()))'
    )
    assert _run(src) == "3\n"


def test_class_def_instance_field_assign_in_init():
    src = (
        'class Point {\n'
        '    init(x | y) {\n'
        '        this.x = x\n'
        '        this.y = y\n'
        '    }\n'
        '}\n'
        'p = Point(3 | 4)\n'
        'coutln(p.x)\n'
        'coutln(p.y)'
    )
    assert _run(src) == "3\n4\n"


def test_class_method_call_uses_this():
    src = (
        'class Counter {\n'
        '    init(start) { this.count = start }\n'
        '    inc() { this.count += 1 }\n'
        '    get() { return this.count }\n'
        '}\n'
        'c = Counter(10)\n'
        'c.inc()\n'
        'c.inc()\n'
        'c.inc()\n'
        'coutln(c.get())'
    )
    assert _run(src) == "13\n"


def test_class_with_no_init_takes_no_args():
    src = (
        'class Empty {\n'
        '    greet() { coutln("hello") }\n'
        '}\n'
        'e = Empty()\n'
        'e.greet()'
    )
    assert _run(src) == "hello\n"


def test_class_with_no_init_rejects_args():
    src = 'class Empty {}\nEmpty(1)'
    with pytest.raises(InterpreterError):
        _run(src)


def test_class_method_calls_other_method():
    src = (
        'class Adder {\n'
        '    init(x) { this.x = x }\n'
        '    double() { return this.x * 2 }\n'
        '    quadruple() { return this.double() * 2 }\n'
        '}\n'
        'a = Adder(5)\n'
        'coutln(a.quadruple())'
    )
    assert _run(src) == "20\n"


def test_class_fields_are_independent_per_instance():
    src = (
        'class Box {\n'
        '    init(v) { this.value = v }\n'
        '}\n'
        'a = Box("first")\n'
        'b = Box("second")\n'
        'coutln(a.value)\n'
        'coutln(b.value)'
    )
    assert _run(src) == "first\nsecond\n"


def test_throw_caught_by_try():
    src = (
        'try {\n'
        '    throw "oops"\n'
        '} catch (e) {\n'
        '    coutln("caught: " + e)\n'
        '}'
    )
    assert _run(src) == "caught: oops\n"


def test_runtime_error_caught():
    src = (
        'try {\n'
        '    x = 1 / 0\n'
        '} catch (e) {\n'
        '    coutln("got error")\n'
        '}'
    )
    assert _run(src) == "got error\n"


def test_undefined_name_caught():
    src = (
        'try {\n'
        '    coutln(nonexistent)\n'
        '} catch (e) {\n'
        '    coutln("undefined caught")\n'
        '}'
    )
    assert _run(src) == "undefined caught\n"


def test_throw_with_dict_value():
    src = (
        'try {\n'
        '    throw {"code": 42 | "msg": "boom"}\n'
        '} catch (e) {\n'
        '    coutln(e["code"])\n'
        '    coutln(e["msg"])\n'
        '}'
    )
    assert _run(src) == "42\nboom\n"


def test_uncaught_throw_propagates():
    src = 'throw "untouched"'
    # Without an enclosing try, _ThrowSignal escapes execute() — Python
    # surfaces it as a BaseException.
    with pytest.raises(BaseException):
        _run(src)


def test_try_block_runs_to_completion_on_success():
    src = (
        'try {\n'
        '    coutln("ok")\n'
        '} catch (e) {\n'
        '    coutln("should not print")\n'
        '}'
    )
    assert _run(src) == "ok\n"


def test_throw_in_function_caught_by_caller():
    src = (
        'funct bad() { throw "from inside" }\n'
        'try {\n'
        '    bad()\n'
        '} catch (e) {\n'
        '    coutln(e)\n'
        '}'
    )
    assert _run(src) == "from inside\n"


def test_fizzbuzz_first_15():
    src = (
        'funct fizzbuzz(n) {\n'
        '    i = 1\n'
        '    while (i <= n) {\n'
        '        if (i % 15 == 0) { coutln("fizzbuzz") }\n'
        '        elseif (i % 3 == 0) { coutln("fizz") }\n'
        '        elseif (i % 5 == 0) { coutln("buzz") }\n'
        '        else { coutln(i) }\n'
        '        i = i + 1\n'
        '    }\n'
        '}\n'
        'fizzbuzz(15)'
    )
    expected = "1\n2\nfizz\n4\nbuzz\nfizz\n7\n8\nfizz\nbuzz\n11\nfizz\n13\n14\nfizzbuzz\n"
    assert _run(src) == expected


def test_closure_captures_lexical_scope():
    # Inside `outer`, calling `inner` should resolve `coutln` from the
    # enclosing scope chain (global), not require it to be a parameter.
    src = (
        'funct outer() {\n'
        '    funct inner() { coutln("inside") }\n'
        '    inner()\n'
        '}\n'
        'outer()'
    )
    assert _run(src) == "inside\n"
