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


def test_math_builtins():
    assert _run("coutln(abs(-5))") == "5\n"
    assert _run("coutln(min(3 | 1 | 2))") == "1\n"
    assert _run("coutln(max(3 | 1 | 2))") == "3\n"
    assert _run("coutln(min([3 | 1 | 2]))") == "1\n"
    assert _run("coutln(pow(2 | 10))") == "1024\n"
    assert _run("coutln(sqrt(16))") == "4.0\n"
    assert _run("coutln(floor(3.9))") == "3\n"
    assert _run("coutln(ceil(3.1))") == "4\n"
    assert _run("coutln(round(2.7))") == "3\n"


def test_math_constants():
    # pi and e are bound as numeric constants.
    assert _run("coutln(round(pi | 2))") == "3.14\n"
    assert _run("coutln(round(e | 2))") == "2.72\n"


def test_type_builtin():
    assert _run("coutln(type(42))") == "int\n"
    assert _run("coutln(type(3.14))") == "float\n"
    assert _run('coutln(type("hi"))') == "string\n"
    assert _run("coutln(type([1 | 2]))") == "list\n"
    assert _run('coutln(type({"a": 1}))') == "dict\n"
    assert _run("coutln(type(true))") == "bool\n"
    assert _run("coutln(type(null))") == "null\n"


def test_type_of_class_instance_is_class_name():
    src = (
        'class Foo {}\n'
        'f = Foo()\n'
        'coutln(type(f))'
    )
    assert _run(src) == "Foo\n"


def test_is_x_predicates():
    assert _run("coutln(is_num(42))") == "true\n"
    assert _run("coutln(is_num(3.14))") == "true\n"
    assert _run('coutln(is_num("hi"))') == "false\n"
    assert _run('coutln(is_str("hi"))') == "true\n"
    assert _run("coutln(is_list([1]))") == "true\n"
    assert _run('coutln(is_dict({"a": 1}))') == "true\n"
    assert _run("coutln(is_bool(true))") == "true\n"
    assert _run("coutln(is_null(null))") == "true\n"
    assert _run("coutln(is_null(0))") == "false\n"


def test_input_builtin(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda prompt="": "alice")
    src = 'name = input("name? ")\ncoutln("hi " + name)'
    assert _run(src) == "hi alice\n"


def test_file_io_round_trip(tmp_path):
    target = tmp_path / "scratch.txt"
    src = (
        f'write_file("{target}" | "hello\\nfile")\n'
        f'content = read_file("{target}")\n'
        f'coutln(content)'
    )
    # The content contains a literal newline after decoding, so output
    # is "hello\nfile\n" (with trailing newline from coutln).
    assert _run(src) == "hello\nfile\n"


def test_rand_int_returns_value_in_range():
    src = (
        'x = rand_int(1 | 10)\n'
        'coutln(x >= 1 and x <= 10)'
    )
    assert _run(src) == "true\n"


def test_rand_float_returns_0_to_1():
    src = (
        'x = rand_float()\n'
        'coutln(x >= 0 and x < 1)'
    )
    assert _run(src) == "true\n"


def test_assert_passes_silently_on_true():
    assert _run("assert(true)\ncoutln(\"ok\")") == "ok\n"


def test_assert_throws_on_false():
    with pytest.raises(InterpreterError):
        _run('assert(false | "boom")')


def test_assert_caught_in_try_block():
    src = (
        'try {\n'
        '    assert(1 == 2 | "math broke")\n'
        '} catch (e) {\n'
        '    coutln(e)\n'
        '}'
    )
    out = _run(src)
    assert "math broke" in out


def test_fstring_simple():
    src = 'name = "alice"\ncoutln(f"hello, {name}!")'
    assert _run(src) == "hello, alice!\n"


def test_fstring_with_number():
    src = 'x = 42\ncoutln(f"x = {x}")'
    assert _run(src) == "x = 42\n"


def test_fstring_with_expression():
    src = 'coutln(f"sum = {1 + 2 * 3}")'
    assert _run(src) == "sum = 7\n"


def test_fstring_no_interpolation_is_just_string():
    assert _run('coutln(f"plain text")') == "plain text\n"


def test_fstring_multiple_interpolations():
    src = 'a = 1\nb = 2\ncoutln(f"{a} + {b} = {a + b}")'
    assert _run(src) == "1 + 2 = 3\n"


def test_fstring_uses_rot_style_stringify():
    # `true` should render as "true", not Python's "True".
    assert _run('coutln(f"flag is {true}")') == "flag is true\n"
    assert _run('coutln(f"empty is {null}")') == "empty is null\n"


def test_fstring_unclosed_brace_errors():
    from rot.errors import ParserError
    with pytest.raises(ParserError):
        _run('coutln(f"oops {x")')


def test_fstring_empty_brace_errors():
    from rot.errors import ParserError
    with pytest.raises(ParserError):
        _run('coutln(f"oops {}")')


def test_str_builtin_uses_rot_style():
    # Updated in v2.9.0 to match f-string conventions.
    assert _run("coutln(str(true))") == "true\n"
    assert _run("coutln(str(null))") == "null\n"
    assert _run("coutln(str(42))") == "42\n"


def test_closure_can_mutate_enclosing_variable():
    """The headline v2.10.0 feature — counter closures now work."""
    src = (
        'funct make_counter() {\n'
        '    count = 0\n'
        '    funct inc() { count += 1 }\n'
        '    inc()\n'
        '    inc()\n'
        '    inc()\n'
        '    coutln(count)\n'
        '}\n'
        'make_counter()'
    )
    assert _run(src) == "3\n"


def test_assignment_in_function_mutates_global():
    src = (
        'x = 10\n'
        'funct change() { x = 99 }\n'
        'change()\n'
        'coutln(x)'
    )
    assert _run(src) == "99\n"


def test_function_param_shadows_outer():
    src = (
        'x = 10\n'
        'funct foo(x) { x = 99 }\n'   # x is a param, set_local — local scope
        'foo(5)\n'
        'coutln(x)'                     # global x unchanged
    )
    assert _run(src) == "10\n"


def test_nested_closure_mutates_outer_scope():
    src = (
        'funct outer() {\n'
        '    x = 1\n'
        '    funct middle() {\n'
        '        funct inner() { x = 99 }\n'
        '        inner()\n'
        '    }\n'
        '    middle()\n'
        '    coutln(x)\n'
        '}\n'
        'outer()'
    )
    assert _run(src) == "99\n"


def test_for_loop_var_is_local():
    # Loop variable shouldn't leak as a global if `i` isn't already declared.
    src = (
        'for i in range(3) {\n'
        '    nothing = i\n'
        '}\n'
        # After the loop, `i` is still bound at this scope (last iter value).
        'coutln(i)'
    )
    assert _run(src) == "2\n"


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
